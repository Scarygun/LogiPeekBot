import asyncio
import os
import logging
import re
from config import LOG_FILE_NAME
from typing import Optional
from datetime import datetime

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

from config import BOT_TOKEN, ADMINS, SUPPORT_GROUP_ID
from telegram import Update
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ChatMemberHandler, CallbackQueryHandler, ContextTypes
import telethon
from search_handler import get_search_conversation_handler, handle_search_page_callback
from admin_handler import get_admin_conversation_handler
from group_handler import get_group_conversation_handler
from contact_handler import get_contact_conversation_handler
from help_handler import get_help_conversation_handler, handle_admin_reply
from feedback_handler import get_feedback_conversation_handler
from broadcast_handler import get_broadcast_conversation_handler
from balance_handler import get_balance_handler
from telethon_client import telethon_client
from database import init_db, add_user_to_json
from menu import set_bot_commands
from language_handler import get_message, get_language_conversation_handler
from keyboards import get_main_menu_keyboard
from persistence import MongoPersistence

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_user_to_json(user.id, user.username)
    welcome_message = get_message(context.user_data, "welcome")
    await update.message.reply_text(welcome_message, reply_markup=get_main_menu_keyboard(context.user_data, get_message))

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

def _should_eager_telethon_connect() -> bool:
    return not _is_vercel_runtime() or os.getenv('EAGER_TELETHON_CONNECT') == '1'

def _should_refresh_bot_commands() -> bool:
    return os.getenv('FORCE_SET_BOT_COMMANDS') == '1' or not _is_vercel_runtime()

async def post_init(application):
    _schedule_background_task(asyncio.to_thread(init_db), "MongoDB indekslarini tayyorlash")
    try:
        if _should_eager_telethon_connect():
            is_authorized = await telethon_client.connect(send_code=False)

            if not is_authorized:
                # Vercel-da terminal bo'lmaydi, shuning uchun faqat log yozamiz
                if os.getenv('VERCEL') or os.getenv('NON_INTERACTIVE'):
                    logger.error("Telethon client avtorizatsiyadan o'tmagan! String session yangilang.")
                else:
                    print("\n" + "="*50)
                    print("TELETHON AVTORIZATSIYASI TALAB QILINADI")
                    print("Siz 'python login.py' buyrug'ini ishlatib tizimga kirishingiz kerak.")
                    print("="*50)

                    try:
                        # Agar foydalanuvchi terminalda bo'lsa, kodni kiritishga urinib ko'ramiz
                        await telethon_client.connect(send_code=True)

                        loop = asyncio.get_running_loop()

                        print("\n>>> Telegram ilovasiga (yoki SMS orqali) kelgan kodni kiriting.")
                        print("(Bekor qilish uchun Ctrl+C bosing)")
                        code = await loop.run_in_executor(None, input, "Kod: ")

                        verification_result = await telethon_client.verify_code(code)

                        if verification_result == True:
                            logger.info("Telethon client muvaffaqiyatli avtorizatsiyadan o'tdi.")
                        elif verification_result == "password_required":
                            print("\n>>> Ikki bosqichli tekshiruv (2FA) paroli talab qilinadi.")
                            password = await loop.run_in_executor(None, input, "Parol: ")
                            if await telethon_client.verify_password(password):
                                logger.info("Telethon client 2FA orqali muvaffaqiyatli ulandi.")
                            else:
                                logger.error("Xato! Noto'g'ri parol.")
                        else:
                            logger.error("Xato! Noto'g'ri kod.")
                    except Exception as e:
                        logger.error(f"Avtorizatsiyada xatolik: {e}")
            else:
                logger.info("Telethon client allaqachon avtorizatsiyadan o'tgan.")
        else:
            logger.info("Vercel startup tezroq bo'lishi uchun Telethon lazy connect rejimida qoldirildi.")

        if _should_refresh_bot_commands():
            await set_bot_commands(application)
        else:
            logger.info("Vercel startup tezligi uchun set_my_commands o'tkazib yuborildi. Zarur bo'lsa FORCE_SET_BOT_COMMANDS=1 ishlating.")
    except Exception as e:
        logger.error(f"Bot initialization error: {e}")

async def post_shutdown(application):
    await telethon_client.disconnect()

def get_application(use_persistence=True):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        return None
    
    builder = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown)
    
    if use_persistence:
        persistence = MongoPersistence()
        builder.persistence(persistence)
        
    application = builder.build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(get_language_conversation_handler())
    application.add_handler(get_search_conversation_handler())
    application.add_handler(CallbackQueryHandler(handle_search_page_callback, pattern=r"^search_"))
    application.add_handler(get_admin_conversation_handler())
    application.add_handler(get_group_conversation_handler())
    application.add_handler(get_contact_conversation_handler())
    application.add_handler(get_help_conversation_handler())
    application.add_handler(get_feedback_conversation_handler())
    application.add_handler(get_broadcast_conversation_handler())
    application.add_handler(get_balance_handler())
    
    # Admin reply handler for support group
    application.add_handler(MessageHandler(filters.REPLY & filters.Chat(chat_id=SUPPORT_GROUP_ID), handle_admin_reply))
    
    return application

def main():
    application = get_application()
    if application:
        application.run_polling()

if __name__ == '__main__':
    main()
