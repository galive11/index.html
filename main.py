import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- خادم ويب وهمي لإبقاء Render شغالاً مجاناً ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "Stream Bot & Mini App is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- الإعدادات ---
BOT_TOKEN = "8832825150:AAEIINN3SmeucO0qQ4DalJ-dJTdsxI_L6LY"
ADMIN_ID = 1957078158
WEB_APP_BASE_URL = "https://galive11.github.io/index.html/"
CHANNEL_USERNAME = "@Jilouka_Streams"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# قواعد البيانات المؤقتة
streamers_db = {}       # { "streamer_username": "stream_url" }
approved_streamers = {} # { streamer_user_id: "streamer_username" }

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_subscribed(user.id, context):
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("✅ تم الاشتراك، تحقق الآن", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            f"مرحباً بك {user.first_name}! 👋\n\nلاستخدام البوت والوصول للبثوث المباشرة، يرجى الاشتراك في القناة أولاً:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    welcome_text = (
        f"مرحباً بك {user.first_name} في منصة البثوث المباشرة! 📺✨\n\n"
        "• أرسل يوزر الستريمر للبحث عن بثه المباشر.\n"
        "• إذا كنت ستريمر معتمد، استخدم الأمر `/setlive [رابط_البث]` لتحديث بثك المباشر."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# --- 👑 أوامر الأدمن (المدير) ---

async def authorize_streamer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة ستريمر معتمد جديد بواسطة الأدمن"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ هذا الأمر مخصص للأدمن فقط.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ الاستخدام الصحيح:\n`/auth [Telegram_User_ID] [streamer_username]`", parse_mode="Markdown")
        return

    try:
        st_id = int(context.args[0])
        st_name = context.args[1].lower().replace("@", "")
        approved_streamers[st_id] = st_name
        await update.message.reply_text(f"✅ تم اعتماد الستريمر `@{st_name}` برقم الآيدي `{st_id}` بنجاح!", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال Telegram User ID بشكل رقمي صحيح.")

async def add_streamer_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة بث مباشر مباشرة عبر الأدمن"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ هذا الأمر مخصص للأدمن فقط.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ استخدم:\n`/add [streamer_username] [stream_url]`", parse_mode="Markdown")
        return

    username = context.args[0].lower().replace("@", "")
    stream_url = context.args[1]
    streamers_db[username] = stream_url
    await update.message.reply_text(f"✅ تم تحديث بث الستريمر `@{username}` بنجاح!", parse_mode="Markdown")

async def remove_streamer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️️ هذا الأمر مخصص للأدمن فقط.")
        return

    if not context.args:
        await update.message.reply_text("❌ استخدم:\n`/remove [streamer_username]`", parse_mode="Markdown")
        return

    username = context.args[0].lower().replace("@", "")
    if username in streamers_db:
        del streamers_db[username]
        await update.message.reply_text(f"🗑 تم إيقاف وحذف بث `@{username}`.")
    else:
        await update.message.reply_text("⚠️ اسم الستريمر غير موجود.")

async def list_streamers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ هذا الأمر مخصص للأدمن فقط.")
        return

    msg = "📺 **قائمة البثوث النشطة حالياً:**\n\n"
    if not streamers_db:
        msg += "لا توجد بثوث نشطة الآن."
    else:
        for user, url in streamers_db.items():
            msg += f"• `@{user}` -> {url}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- 🎮 أوامر الستريمر المعتمد ---

async def set_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يستخدمها الستريمر لتحديث رابط بثه المباشر بنفسه"""
    user_id = update.effective_user.id

    if user_id not in approved_streamers and user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ ليس لديك صلاحية ستريمر معتمد! تواصل مع الأدمن للحصول على الصلاحية.")
        return

    if not context.args:
        await update.message.reply_text("❌ يرجى إرفاق رابط البث المباشر. مثال:\n`/setlive https://my-server.com/live/streamer1.m3u8`", parse_mode="Markdown")
        return

    st_name = approved_streamers.get(user_id, update.effective_user.username or f"user_{user_id}").lower()
    stream_url = context.args[0]

    streamers_db[st_name] = stream_url
    await update.message.reply_text(
        f"🎉 **تم تفعيل بثك المباشر بنجاح!**\nاسم حسابك: `@{st_name}`\nرابط البث: {stream_url}\n\nيمكن للمتابعين الآن مشاهدتك عبر الميني أب!",
        parse_mode="Markdown"
    )

# --- معالجة الرسائل والبحث للمتابعين ---

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
        await update.message.reply_text(
            f"🔴 **البث المباشر لـ @{query_username} متاح الآن!**\nاضغط على الزر أدناه لمشاهدة البث مباشرة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ لا يوجد بث مباشر نشط حالياً للستريمر `@{query_username}`.",
            parse_mode="Markdown"
        )

def main():
    keep_alive()

    app = Application.builder().token(BOT_TOKEN).build()

    # الأوامر العامة
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))

    # أوامر الأدمن
    app.add_handler(CommandHandler("auth", authorize_streamer))
    app.add_handler(CommandHandler("add", add_streamer_admin))
    app.add_handler(CommandHandler("remove", remove_streamer))
    app.add_handler(CommandHandler("list", list_streamers))

    # أوامر الستريمرز
    app.add_handler(CommandHandler("setlive", set_live))

    # البحث
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("البوت يعمل الآن بنظام الستريمرز المستقلين...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
