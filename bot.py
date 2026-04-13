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

from config import BOT_TOKEN, ADMINS, SUPPORT_GROUP_ID
from telegram import Update
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ChatMemberHandler, CallbackQueryHandler, ContextTypes
import telethon
from search_handler import get_search_conversation_handler
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

async def post_init(application):
    init_db()
    try:
        # Avval sessiya bormi-yo'qligini tekshiramiz
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
                    
                    import asyncio
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
            
        await set_bot_commands(application)
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

if __name__ == '__main__':
    main()