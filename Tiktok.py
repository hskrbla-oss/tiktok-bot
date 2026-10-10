import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# إعداد نظام التسجيل لمراقبة الأخطاء وتشغيل البوت
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. إعداد قاعدة بيانات SQLite وحفظها محلياً باسم tiktok_bot.db
def init_db():
    conn = sqlite3.connect('tiktok_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# دوال مساعدة للتعامل مع قاعدة البيانات
def get_last_account():
    conn = sqlite3.connect('tiktok_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM accounts ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def add_account_to_db(username):
    conn = sqlite3.connect('tiktok_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO accounts (username) VALUES (?)', (username,))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_total_accounts():
    conn = sqlite3.connect('tiktok_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM accounts')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# 2. أمر البدء (Start)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت تبادل تفاعل ومتابعي تيك توك 🚀\n\n"
        "لإدراج حسابك في القائمة التبادلية، أرسل الأمر:\n"
        "`/add @معرف_حسابك`\n\n"
        "لمعرفة عدد الحسابات المسجلة أرسل الأمر:\n"
        "`/stats`",
        parse_mode="Markdown"
    )

# 3. أمر إضافة حساب جديد (/add)
async def add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ يرجى كتابة معرف حسابك بعد الأمر بشكل صحيح، مثال:\n`/add @your_tiktok_username`",
            parse_mode="Markdown"
        )
        return
    
    user_account = context.args[0]
    last_acc = get_last_account()
    
    # إذا وجدت حسابات مسبقة، نجبر المستخدم الجديد على متابعة آخر حساب أضيف
    if last_acc:
        keyboard = [
            [InlineKeyboardButton("1. اضغط هنا لمتابعة الحساب", url=f"https://www.tiktok.com/{last_acc}")],
            [InlineKeyboardButton("2. تم المتابعة (تأكيد وإضافة حسابي)", callback_data=f"confirm_{user_account}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"لإضافة حسابك `{user_account}` إلى القائمة، يجب عليك أولاً متابعة أحدث حساب مضاف:\n👉 {last_acc}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # إذا كانت القائمة فارغة كلياً، يُضاف كأول حساب مباشرة
        if add_account_to_db(user_account):
            await update.message.reply_text(
                f"✅ تمت إضافة حسابك `{user_account}` بنجاح كأول حساب في القائمة!",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ هذا الحساب مسجل مسبقاً في القائمة.")

# 4. معالجة الضغط على أزرار التفاعل (Callback Query)
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("confirm_"):
        new_acc = query.data.split("confirm_")[1]
        if add_account_to_db(new_acc):
            await query.edit_message_text(
                f"🎉 شكراً لك!\nتم التحقق وإضافة حسابك `{new_acc}` إلى قاعدة البيانات بنجاح لكي يظهر للمستخدمين القادمين.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("⚠️ يبدو أن هذا الحساب مسجل مسبقاً في النظام بالفعل.")

# 5. أمر إحصائيات البوت (/stats)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = get_total_accounts()
    await update.message.reply_text(
        f"📊 **إحصائيات البوت:**\n\n"
        f"إجمالي الحسابات المسجلة لتبادل التفاعل: `{total}` حساب.",
        parse_mode="Markdown"
    )

if __name__ == '__main__':
    # التوكن الخاص بك جاهز ومضاف هنا
    TOKEN = "8870073458:AAGRm6RJb0WCyA_OL7clO2FqMGdo_SC3skQ"
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # ربط الأوامر بالدوال البرمجية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_account))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("البوت يعمل الآن بكفاءة مع قاعدة البيانات...")
    app.run_polling()
