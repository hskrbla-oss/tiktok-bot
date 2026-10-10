import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# إعداد نظام التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ADMIN_ID = 8844734839

# 1. إعداد قاعدة بيانات SQLite
def init_db():
    conn = sqlite3.connect('tiktok_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            video_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_last_task():
    conn = sqlite3.connect('tiktok_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, video_url FROM accounts ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return row if row else (None, None)

def add_task_to_db(username, video_url):
    conn = sqlite3.connect('tiktok_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO accounts (username, video_url) VALUES (?, ?)', (username, video_url))
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
    context.user_data.clear()
    await update.message.reply_text(
        "مرحباً بك في بوت تبادل التفاعل الشامل (متابعة + لايك للفيديو) 🚀\n\n"
        "• لإضافة حسابك ومقطعك، أرسل معرف حسابك في تيك توك أولاً (مثال: @username)\n"
        "• لمعرفة عدد الحسابات المسجلة: /stats"
    )

# 3. إدارة الخطوات بلغة مبسطة وآمنة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "إلغاء":
        context.user_data.clear()
        await update.message.reply_text("❌ تم إلغاء العملية بنجاح.")
        return

    # الخطوة أ: استقبال معرف التيك توك
    if not text.startswith('/') and 'temp_username' not in context.user_data and 'pending_account' not in context.user_data:
        user_account = text if text.startswith('@') else '@' + text
        context.user_data['temp_username'] = user_account
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process")]]
        await update.message.reply_text(
            f"تم حفظ المعرف: {user_account}\n\n"
            "🔗 الخطوة الثانية: أرسل الآن رابط مقطع الفيديو على تيك توك الذي تريد أن يقوم المستخدمون بعمل (لايك) عليه:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # الخطوة ب: استقبال رابط الفيديو
    if not text.startswith('/') and 'temp_username' in context.user_data and 'pending_video' not in context.user_data:
        video_url = text
        user_account = context.user_data['temp_username']
        context.user_data['pending_account'] = user_account
        context.user_data['pending_video'] = video_url
        
        context.user_data.pop('temp_username', None)
        
        last_acc, last_video = get_last_task()
        
        if last_acc and last_video:
            clean_acc = last_acc.replace('@', '')
            keyboard = [
                [InlineKeyboardButton("1. 👤 متابعة الحساب", url=f"https://www.tiktok.com/@{clean_acc}")],
                [InlineKeyboardButton("2. ❤️ وضع لايك للفيديو", url=last_video)],
                [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"متطلبات النشر لتفعيل حسابك:\n\n"
                f"يجب عليك التفاعل مع آخر عضو:\n"
                f"• متابعة الحساب: {last_acc}\n"
                f"• الإعجاب بالفيديو الخاص به.\n\n"
                f"📸 الخطوة الأخيرة: بعد إتمام التفاعل، أرسل لقطة الشاشة (Screenshot) هنا للمراجعة!",
                reply_markup=reply_markup
            )
        else:
            if add_task_to_db(user_account, video_url):
                context.user_data.clear()
                await update.message.reply_text("🎉 تمت إضافة حسابك ومقطعك بنجاح كأول حساب في القائمة!")
            else:
                context.user_data.clear()
                await update.message.reply_text("⚠️ هذا الحساب مسجل مسبقاً في القائمة.")

# 4. استقبال لقطة الشاشة وإرسالها للمشرف
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_username = update.message.from_user.username or "بدون معرف"
    pending_acc = context.user_data.get('pending_account')
    pending_video = context.user_data.get('pending_video')
    
    if not pending_acc or not pending_video:
        await update.message.reply_text("⚠️ الرجاء إرسال معرف تيك توك ورابط الفيديو أولاً باتباع الخطوات.")
        return
    
    photo_file_id = update.message.photo[-1].file_id
    
    keyboard = [
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_file_id,
        caption=f"طلب تفعيل تفاعل جديد (متابعة + لايك):\n\n"
                f"صاحب الحساب: @{user_username} (ID: {user_id})\n"
                f"تيك توك المطلوب إضافته: {pending_acc}\n"
                f"رابط الفيديو المطلوب نشره: {pending_video}",
        reply_markup=reply_markup
    )
    
    context.user_data.clear()
    await update.message.reply_text("⏳ تم إرسال لقطة الشاشة بنجاح إلى المشرف! سيتم مراجعتها وقبولها قريباً.")

# 5. معالجة الأزرار
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "cancel_process":
        await query.message.edit_text("❌ تم إلغاء العملية.")
        return

    if data.startswith("accept_"):
        target_user_id = int(data.split("_")[1])
        caption = query.message.caption
        try:
            lines = caption.split('\n')
            acc_line = [l for l in lines if "تيك توك المطلوب إضافته:" in l][0]
            vid_line = [l for l in lines if "رابط الفيديو المطلوب نشره:" in l][0]
            
            new_acc = acc_line.split(": ")[1].strip()
            new_vid = vid_line.split(": ")[1].strip()
            
            if add_task_to_db(new_acc, new_vid):
                await query.edit_message_caption(caption=query.message.caption + "\n\n✅ تمت الموافقة وإضافة الحساب والفيديو بنجاح للقائمة!")
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 تهانينا! تم قبول لقطة الشاشة وإضافة حسابك {new_acc} ومقطعك بنجاح."
                )
            else:
                await query.edit_message_caption(caption=query.message.caption + "\n\n⚠️ الحساب مسجل مسبقاً بالفعل.")
        except Exception as e:
            await query.edit_message_caption(caption=query.message.caption + f"\n\n❌ خطأ: {str(e)}")
            
    elif data.startswith("reject_"):
        target_user_id = int(data.split("_")[1])
        await query.edit_message_caption(caption=query.message.caption + "\n\n❌ تم رفض الطلب.")
        await context.bot.send_message(
            chat_id=target_user_id,
            text="❌ عذراً، تم رفض لقطة الشاشة الخاصة بك من قِبل المشرف."
        )

# 6. الإحصائيات
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = get_total_accounts()
    await update.message.reply_text(f"📊 إحصائيات البوت:\n\nإجمالي الحسابات والمقاطع المسجلة: {total} حساب.")

if __name__ == '__main__':
    TOKEN = "8870073458:AAGRm6RJb0WCyA_OL7clO2FqMGdo_SC3skQ"
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("البوت يعمل الآن باستقرار تام...")
    app.run_polling()
