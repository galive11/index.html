import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات والبيانات الخاصة بك ---
BOT_TOKEN = "8832825150:AAEIINN3SmeucO0qQ4DalJ-dJTdsxI_L6LY"
ADMIN_ID = 1957078158
WEB_APP_BASE_URL = "https://galive11.github.io/index.html/"
CHANNEL_USERNAME = "@Jilouka_Streams"  # قناة الاشتراك الإجباري

# تهيئة سجل التشغيل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# قاعدة بيانات مؤقتة لتخزين الستريمرز وروابط البث
streamers_db = {}

# --- وظيفة التحقق من الاشتراك في القناة ---
async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return True

# --- أمر البداية /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not await is_subscribed(user.id, context):
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("✅ تم الاشتراك، تحقق الآن", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"مرحباً بك {user.first_name}! 👋\n\nلاستخدام البوت والوصول للبثوث المباشرة، يرجى الاشتراك في قناتنا أولاً:",
            reply_markup=reply_markup
        )
        return

    welcome_text = (
        f"مرحباً بك {user.first_name} في منصة البثوث المباشرة! 📺✨\n\n"
        "أرسل يوزر الستريمر (مثل `streamer1`) للبحث عن بث مباشر أو للوصول للرابط الخاص به."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# --- لوحة التحكم والأوامر للأدمن فقط ---
async def add_streamer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ هذا الأمر مخصص للأدمن فقط.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ الصيغة الخاطئة! استخدم:\n`/add [streamer_username] [stream_url]`", parse_mode="Markdown")
        return

    username = context.args[0].lower().replace("@", "")
    stream_url = context.args[1]

    streamers_db[username] = stream_url
    await update.message.reply_text(f"✅ تم إضافة/تحديث الستريمر `@{username}` بنجاح!", parse_mode="Markdown")

async def remove_streamer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ هذا الأمر مخصص للأدمن فقط.")
        return

    if not context.args:
        await update.message.reply_text("❌ استخدم:\n`/remove [streamer_username]`", parse_mode="Markdown")
        return

    username = context.args[0].lower().replace("@", "")
    if username in streamers_db:
        del streamers_db[username]
        await update.message.reply_text(f"🗑 تم حذف الستريمر `@{username}`.")
    else:
        await update.message.reply_text(f"⚠️ الستريمر `@{username}` غير موجود بالقائمة.")

async def list_streamers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ هذا الأمر مخصص للأدمن فقط.")
        return

    if not streamers_db:
        await update.message.reply_text("📋 لا يوجد ستريمرز مضافون حالياً.")
        return

    msg = "📺 **قائمة الستريمرز المضافين:**\n\n"
    for user, url in streamers_db.items():
        msg += f"• `@{user}` -> {url}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- معالجة أرسال اسم الستريمر من المستخدم ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_subscribed(user.id, context):
        await update.message.reply_text("⚠️ يرجى الاشتراك في القناة أولاً لتتمكن من استخدام البوت.")
        return

    query_username = update.message.text.strip().lower().replace("@", "")

    if query_username in streamers_db:
        stream_url = streamers_db[query_username]
        web_app_full_url = f"{WEB_APP_BASE_URL}?streamer={query_username}&url={stream_url}"

        keyboard = [
            [InlineKeyboardButton("📺 مشاهدة البث المباشر الآن", web_app=WebAppInfo(url=web_app_full_url))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🔴 **البث المباشر لـ @{query_username} متاح الآن!**\nاضغط على الزر أدناه لمشاهدة البث:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ لم يتم العثور على بث مباشر نشط للستريمر `@{query_username}` حالياً.",
            parse_mode="Markdown"
        )

# --- تشغيل التطبيق ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # الأوامر العامة
    app.add_handler(CommandHandler("start", start))

    # أوامر الأدمن
    app.add_handler(CommandHandler("add", add_streamer))
    app.add_handler(CommandHandler("remove", remove_streamer))
    app.add_handler(CommandHandler("list", list_streamers))

    # الرسائل النصية والبحث
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("البوت يعمل الآن...")
    # إغلاق أي جلسات معلقة أو متداخلة تلقائياً
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
