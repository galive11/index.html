import os
import json
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
WEB_APP_BASE_URL = "https://galive11.github.io/"
CHANNEL_USERNAME = "@Jilouka_Streams"
DATA_FILE = "data.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# قواعد البيانات في الذاكرة
streamers_db = {}
approved_streamers = {}

def load_data():
    global streamers_db, approved_streamers
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                streamers_db = data.get("streamers_db", {})
                approved = data.get("approved_streamers", {})
                approved_streamers = {int(k): v for k, v in approved.items()}
                logging.info("تم تحميل البيانات من الملف بنجاح.")
        except Exception as e:
            logging.error(f"خطأ في قراءة ملف البيانات: {e}")

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "streamers_db": streamers_db,
                "approved_streamers": approved_streamers
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"خطأ في حفظ البيانات: {e}")

# تحميل البيانات فور تشغيل السكريبت
load_data()

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
        "• للستريمر المعتمد: ربط قناة Twitch عبر الأمر `/setchannel [اسم_القناة]`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# --- 👑 أوامر الأدمن ---

async def authorize_streamer(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        streamers_db[st_name] = st_name
        save_data()
        await update.message.reply_text(f"✅ تم اعتماد الستريمر `@{st_name}` برقم الآيدي `{st_id}` بنجاح وحفظ البيانات!", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال Telegram User ID بشكل رقمي صحيح.")

async def add_streamer_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ هذا الأمر مخصص للأدمن فقط.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ استخدم:\n`/add [streamer_username] [twitch_channel_name]`", parse_mode="Markdown")
        return

    username = context.args[0].lower().replace("@", "")
    twitch_channel = context.args[1].lower().replace("@", "")
    streamers_db[username] = twitch_channel
    save_data()
    await update.message.reply_text(f"✅ تم ربط الستريمر `@{username}` بقناة Twitch: `{twitch_channel}` بنجاح!", parse_mode="Markdown")

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
        save_data()
        await update.message.reply_text(f"🗑 تم إيقاف وحذف بث `@{username}`.")
    else:
        await update.message.reply_text("⚠️ اسم الستريمر غير موجود.")

async def list_streamers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ هذا الأمر مخصص للأدمن فقط.")
        return

    msg = "📺 **قائمة الستريمرز المسجلين حالياً:**\n\n"
    if not streamers_db:
        msg += "لا يوجد ستريمرز مسجلين الآن."
    else:
        for user, tw_chan in streamers_db.items():
            msg += f"• `@{user}` -> Twitch: `{tw_chan}`\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- 🎮 أوامر الستريمر ---

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in approved_streamers and user_id != ADMIN_ID:
        await update.message.reply_text("⚠️ ليس لديك صلاحية ستريمر معتمد! تواصل مع الأدمن للحصول على الصلاحية.")
        return

    if not context.args:
        await update.message.reply_text("❌ يرجى إرفاق اسم قناتك على Twitch. مثال:\n`/setchannel 1stremer_1`", parse_mode="Markdown")
        return

    st_name = approved_streamers.get(user_id, update.effective_user.username or f"user_{user_id}").lower().replace("@", "")
    twitch_channel = context.args[0].lower().replace("@", "")

    streamers_db[st_name] = twitch_channel
    save_data()
    await update.message.reply_text(
        f"🎉 **تم ربط قناتك بنجاح!**\nاسم حسابك بالبوت: `@{st_name}`\nقناة Twitch: `{twitch_channel}`\n\nالان بمجرد بدء البث من PRISM سيظهر بثك تلقائياً للمتابعين عبر الميني أب!",
        parse_mode="Markdown"
    )

async def set_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_channel(update, context)

# --- معالجة الرسائل والبحث ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_subscribed(user.id, context):
        await update.message.reply_text("⚠️ يرجى الاشتراك في القناة أولاً لتتمكن من استخدام البوت.")
        return

    query_username = update.message.text.strip().lower().replace("@", "")

    twitch_channel = None
    if query_username in streamers_db:
        twitch_channel = streamers_db[query_username]
    else:
        for st_id, st_name in approved_streamers.items():
            if st_name.lower() == query_username:
                twitch_channel = query_username
                break

    if twitch_channel:
        web_app_full_url = f"{WEB_APP_BASE_URL}?streamer={twitch_channel}"

        # استخدام رابط مباشر (url) لفتح الميني أب وضمان استجابة الزر لدى كافة المستخدمين
        keyboard = [
            [InlineKeyboardButton("📺 مشاهدة البث المباشر الآن", url=web_app_full_url)]
        ]
        await update.message.reply_text(
            f"🔴 **البث المباشر لـ @{query_username} متاح الآن!**\nاضغط على الزر أدناه لمشاهدة البث مباشرة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ لا يوجد بث مباشر مسجل حالياً للستريمر `@{query_username}`.",
            parse_mode="Markdown"
        )

def main():
    keep_alive()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))

    app.add_handler(CommandHandler("auth", authorize_streamer))
    app.add_handler(CommandHandler("add", add_streamer_admin))
    app.add_handler(CommandHandler("remove", remove_streamer))
    app.add_handler(CommandHandler("list", list_streamers))

    app.add_handler(CommandHandler("setchannel", set_channel))
    app.add_handler(CommandHandler("setlive", set_live))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("البوت شغال الآن...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
