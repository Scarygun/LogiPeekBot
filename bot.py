import asyncio
import os
import logging
from config import LOG_FILE_NAME

# Log konfiguratsiyasi
handlers = [logging.StreamHandler()]

# Vercel-da faqat StreamHandler ishlatamiz (faylga ruxsat yo'qligi sababli)
if not os.getenv('VERCEL'):
    try:
        handlers.append(logging.FileHandler(LOG_FILE_NAME, encoding='utf-8'))
    except Exception as e:
        print(f"Log faylini ochib bo'lmadi: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)
_background_tasks = set()

from config import BOT_TOKEN, OWNER_ID
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from search_handler import get_search_conversation_handler, handle_search_page_callback

from help_handler import get_help_conversation_handler, handle_admin_reply
from balance_handler import get_balance_handler
from login_handler import get_login_conversation_handler
from register_handler import get_register_conversation_handler
from forgot_password_handler import get_forgot_password_conversation_handler
from profile_handler import get_profile_handler, handle_profile_callback
from database import init_db, add_user_to_json
from menu import set_bot_commands
from language_handler import get_message, get_language_conversation_handler
from keyboards import get_main_menu_keyboard
from telegram.ext import PicklePersistence

from database import _read_json
from config import USERS_JSON_FILE
from keyboards import get_auth_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_user_to_json(user.id, user.username)
    welcome_message = get_message(context.user_data, "welcome")
    
    # Check if user is logged in
    users = _read_json(USERS_JSON_FILE, [])
    is_logged_in = False
    if isinstance(users, list):
        for u in users:
            if str(u.get("user_id")) == str(user.id) and u.get("vigo_phone"):
                is_logged_in = True
                break
    elif isinstance(users, dict):
        if str(user.id) in users and users[str(user.id)].get("vigo_phone"):
            is_logged_in = True

    if is_logged_in:
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
    else:
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users = _read_json(USERS_JSON_FILE, [])
    is_logged_in = False
    if isinstance(users, list):
        for u in users:
            if str(u.get("user_id")) == str(user.id) and u.get("vigo_phone"):
                is_logged_in = True
                break
    elif isinstance(users, dict):
        if str(user.id) in users and users[str(user.id)].get("vigo_phone"):
            is_logged_in = True

    if is_logged_in:
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
    else:
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        
    await update.message.reply_text(
        get_message(context.user_data, "main_menu"),
        reply_markup=reply_markup
    )

def _track_background_task(task, description: str):
    _background_tasks.add(task)

    def _on_done(done_task):
        _background_tasks.discard(done_task)
        try:
            done_task.result()
        except Exception as exc:
            logger.error("%s xatolik bilan tugadi: %s", description, exc)

    task.add_done_callback(_on_done)
    return task

def _schedule_background_task(coro, description: str):
    return _track_background_task(asyncio.create_task(coro), description)

def _is_vercel_runtime() -> bool:
    return bool(os.getenv('VERCEL'))

def _should_refresh_bot_commands() -> bool:
    return os.getenv('FORCE_SET_BOT_COMMANDS') == '1' or not _is_vercel_runtime()



from payment_checker import payment_checker_job

async def post_init(application):
    _schedule_background_task(asyncio.to_thread(init_db), "MongoDB indekslarini tayyorlash")
    _schedule_background_task(payment_checker_job(application), "Backend to'lovlarini tekshirish")
    try:
        if _should_refresh_bot_commands():
            await set_bot_commands(application)
        else:
            logger.info("Vercel startup tezligi uchun set_my_commands o'tkazib yuborildi. Zarur bo'lsa FORCE_SET_BOT_COMMANDS=1 ishlating.")
    except Exception as e:
        logger.error(f"Bot initialization error: {e}")

async def post_shutdown(application):
    pass

def get_application(use_persistence=True):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        return None
    
    builder = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown)
    
    if use_persistence:
        persistence = PicklePersistence(filepath="bot_data.pickle")
        builder.persistence(persistence)
        
    application = builder.build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(get_language_conversation_handler())
    application.add_handler(get_search_conversation_handler())
    application.add_handler(CallbackQueryHandler(handle_search_page_callback, pattern=r"^search_"))
    application.add_handler(get_login_conversation_handler())
    application.add_handler(get_register_conversation_handler())
    application.add_handler(get_forgot_password_conversation_handler())
    application.add_handler(get_help_conversation_handler())
    application.add_handler(get_profile_handler())
    application.add_handler(CallbackQueryHandler(handle_profile_callback, pattern=r"^profile_"))
    application.add_handler(get_balance_handler())
    
    # Umumiy Orqaga tugmasi (konversatsiyadan tashqarida bosilganda bosh menyuga qaytaradi)
    from language_handler import MESSAGES
    back_buttons = [MESSAGES[l]["back_button"].strip() for l in MESSAGES if "back_button" in MESSAGES[l]]
    application.add_handler(MessageHandler(filters.Text(back_buttons), back_to_main_menu))
    
    # Admin reply handler for owner
    application.add_handler(MessageHandler(filters.REPLY & filters.Chat(chat_id=OWNER_ID), handle_admin_reply))
    
    return application

def main():
    application = get_application()
    if application:
        application.run_polling()

if __name__ == '__main__':
    main()
