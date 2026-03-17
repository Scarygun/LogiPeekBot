import os
import logging
import re
from config import LOG_FILE_NAME
from typing import Optional
from datetime import datetime

# Log konfiguratsiyasi
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_NAME, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from config import BOT_TOKEN, ADMINS, SUPPORT_GROUP_ID
from telegram import Update
import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ChatMemberHandler, CallbackQueryHandler, ContextTypes
import telethon
from search_handler import get_search_conversation_handler
from admin_handler import get_admin_conversation_handler
from telethon_client import telethon_client
from database import init_db, add_user_to_json
from menu import set_bot_commands
from language_handler import get_message, get_language_conversation_handler
from keyboards import get_main_menu_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_user_to_json(user.id, user.username)
    welcome_message = get_message(user.id, "welcome_message")
    await update.message.reply_text(welcome_message, reply_markup=get_main_menu_keyboard(user.id))

async def post_init(application):
    init_db()
    try:
        # Avval sessiya bormi-yo'qligini tekshiramiz
        is_authorized = await telethon_client.connect(send_code=False)
        
        if not is_authorized:
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
                    print("Muvaffaqiyatli! Bot ishga tushmoqda...")
                elif verification_result == "password_required":
                    print("\n>>> Ikki bosqichli tekshiruv (2FA) paroli talab qilinadi.")
                    password = await loop.run_in_executor(None, input, "Parol: ")
                    if await telethon_client.verify_password(password):
                        logger.info("Telethon client 2FA orqali muvaffaqiyatli ulandi.")
                        print("Muvaffaqiyatli! Bot ishga tushmoqda...")
                    else:
                        print("Xato! Noto'g'ri parol kiritildi. Bot to'xtatilmoqda.")
                        import sys
                        sys.exit(1)
                else:
                    print("Xato! Noto'g'ri kod kiritildi. Bot to'xtatilmoqda.")
                    import sys
                    sys.exit(1)
            except telethon.errors.FloodWaitError as e:
                wait_hours = e.seconds // 3600
                wait_minutes = (e.seconds % 3600) // 60
                print("\n" + "!"*50)
                print("TELEGRAM CHEKLOVI (FLOOD WAIT)")
                print(f"Kutish vaqti: {e.seconds} soniya (~{wait_hours} soat {wait_minutes} daqiqa).")
                print("Hozircha tizimga kirib bo'lmaydi. Bot to'xtatilmoqda.")
                print("!"*50 + "\n")
                import sys
                sys.exit(1)
            except Exception as e:
                print(f"Avtorizatsiyada xatolik: {e}")
                print("Iltimos, 'python login.py' buyrug'ini terminalda alohida ishga tushirib ko'ring.")
                print("Bot to'xtatilmoqda.")
                import sys
                sys.exit(1)
        else:
            logger.info("Telethon client allaqachon avtorizatsiyadan o'tgan.")
            
        await set_bot_commands(application)
    except telethon.errors.FloodWaitError as e:
        wait_hours = e.seconds // 3600
        wait_minutes = (e.seconds % 3600) // 60
        print("\n" + "!"*50)
        print("TELEGRAM CHEKLOVI (FLOOD WAIT)")
        print(f"Juda ko'p urinishlar tufayli Telegram sizni blokladi.")
        print(f"Kutish vaqti: {e.seconds} soniya (~{wait_hours} soat {wait_minutes} daqiqa).")
        print("!"*50 + "\n")
        logger.error(f"FloodWaitError: {e.seconds} seconds")
    except Exception as e:
        logger.error(f"Bot initialization error: {e}")

async def post_shutdown(application):
    await telethon_client.disconnect()

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        return
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(get_language_conversation_handler())
    application.add_handler(get_search_conversation_handler())
    application.add_handler(get_admin_conversation_handler())
    application.run_polling()

if __name__ == '__main__':
    main()