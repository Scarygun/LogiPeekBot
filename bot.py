import os
import logging
import re
from config import LOG_FILE_NAME # LOG_FILE_NAME bu yerga ko'chirildi
from typing import Optional # Add this import

# Log konfiguratsiyasi
# Asosiy loggerni sozlash
logging.basicConfig(
    level=logging.INFO, # Umumiy log levelini INFO ga o'zgartirdik
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_NAME, encoding='utf-8'),  # Loglarni faylga yozish
        logging.StreamHandler()  # Loglarni konsolga chiqarish
    ]
)
logger = logging.getLogger(__name__)

# Httpx log levelini sozlash (ko'p ma'lumot chiqarmaslik uchun)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telethon").setLevel(logging.INFO)
logging.getLogger('admin_handler').setLevel(logging.DEBUG) # Add this line

import sqlite3 # Yangi import
# import gspread # Yangi import (ko'chirildi)
# from oauth2client.service_account import ServiceAccountCredentials # Yangi import (ko'chirildi)
from config import BOT_TOKEN, ADMINS, SUPPORT_GROUP_ID # LOG_FILE_NAME endi alohida import qilinadi
from telegram import Update # Added Update
import telegram # Added for telegram.error.Conflict
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ChatMemberHandler, CallbackQueryHandler, ContextTypes # Added ContextTypes
from search_handler import get_search_conversation_handler
from group_handler import get_group_conversation_handler
from contact_handler import get_contact_conversation_handler
from admin_handler import get_admin_conversation_handler
from telethon_client import telethon_client
from broadcast_handler import get_broadcast_conversation_handler
from feedback_handler import get_feedback_conversation_handler
from help_handler import get_help_conversation_handler, handle_admin_reply
from database import init_db, add_group as db_add_group, remove_group as db_remove_group, get_all_groups as db_get_all_groups, add_user_to_json, get_user_count_from_json, get_group_count_from_json # Yangilangan importlar
from config import USER_API_ID, USER_API_HASH
from menu import set_bot_commands
from language_handler import get_message, get_language_conversation_handler, LanguageStates, start_language_selection

from keyboards import get_main_menu_keyboard # Yangi import
# from datetime import datetime # Yangi import

# --- DB setup (oddiy) ---
# conn = sqlite3.connect("groups.db") # Global ulanish olib tashlandi
# cur = conn.cursor() # Global kursor olib tashlandi
# cur.execute("""
# CREATE TABLE IF NOT EXISTS groups (
#     chat_id INTEGER PRIMARY KEY,
#     title TEXT,
#     saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# )""")
# conn.commit()

async def add_group(chat_id: int, title: Optional[str]): # Changed str | None to Optional[str]
    await db_add_group(chat_id, title) # database.py dagi funksiyani chaqirish

async def remove_group(chat_id: int):
    await db_remove_group(chat_id) # database.py dagi funksiyani chaqirish

async def get_all_groups():
    return await db_get_all_groups() # database.py dagi funksiyani chaqirish

# --- Google Sheets setup (qolgan qismi database.py ga ko'chirildi) ---
# Google Sheets client
# _gsheet_client = None

# def get_gsheet_client():
#     global _gsheet_client
#     if _gsheet_client is None:
#         try:
#             scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#             creds = ServiceAccountCredentials.from_json_keyfile_name(SHEETS_CREDENTIALS_FILE, scope)
#             _gsheet_client = gspread.authorize(creds)
#             logger.info("Google Sheets client muvaffaqiyatli ishga tushirildi.")
#         except Exception as e:
#             logger.error(f"Google Sheets client ishga tushirishda xato: {e}")
#             _gsheet_client = None # Xato bo'lsa, qayta urinish uchun None ga o'rnatamiz
#     return _gsheet_client

# def save_user_to_sheets(user_id: int, username: str | None, full_name: str | None):
#     try:
#         client = get_gsheet_client()
#         if client:
#             spreadsheet = client.open(SHEETS_SPREADSHEET_NAME)
#             worksheet = spreadsheet.sheet1 # Birinchi sahifa
            
#             # user_id allaqachon mavjudligini tekshiramiz
#             user_ids = worksheet.col_values(1) # Birinchi ustun (user_id) qiymatlarini olamiz
#             if str(user_id) in user_ids:
#                 logger.info(f"User {user_id} allaqachon Google Sheets da mavjud. Yangilanmadi.")
#                 return

#             # Yangi qator qo'shamiz
#             row = [user_id, username, str(datetime.now()), full_name]
#             logger.debug(f"Attempting to append row to Google Sheets: {row}")
#             worksheet.append_row(row)
#             logger.info(f"User {user_id} Google Sheets ga saqlandi.")
#         else:
#             logger.error("Google Sheets client mavjud emas. Foydalanuvchi ma'lumotlari saqlanmadi.")
#     except Exception as e:
#         logger.error(f"Google Sheets ga foydalanuvchi ma'lumotlarini saqlashda xato: {e.__class__.__name__}: {e}")

# get_user_count_from_sheets funksiyasi database.py ga ko'chirildi

async def start(update, context):
    # Start komandasi
    user_id = update.effective_user.id
    username = update.effective_user.username
    user_language = context.user_data.get('language', 'uz') # Default til 'uz'
    
    await add_user_to_json(user_id, username)
    
    if not user_language:
        return await start_language_selection(update, context)
    
    reply_markup = get_main_menu_keyboard(context.user_data, get_message)

    await update.message.reply_text(
        get_message(context.user_data, 'start_message'),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def help_command(update, context):
    await update.message.reply_text(get_message(context.user_data, "help_message"))



async def check_balance(update, context):
    # Balans tekshirish funksiyasi
    await update.message.reply_text(
        get_message(context.user_data, "balance_check_title") + "\n\n" +
        get_message(context.user_data, "current_balance", balance=0) + "\n\n" +
        get_message(context.user_data, "contact_admin"),
        parse_mode="HTML"
    )

async def on_chat_member_update(update, context):
    # Bu handler bot status o'zgarganda chaqiriladi
    chat_member = update.my_chat_member
    if not chat_member:
        chat_member = update.chat_member
        
    if not chat_member:
        logger.warning("Chat member update received but no chat_member found.")
        return

    chat_id = chat_member.chat.id
    chat_title = chat_member.chat.title
    
    logger.info(f"Chat Member Update: Chat ID: {chat_id}, Title: {chat_title}")
    print(f"DEBUG: Chat ID: {chat_id}, Title: {chat_title}") # For immediate terminal visibility

    # Botning o'zgarishini aniqlaymiz
    if chat_member.new_chat_member.user.id == context.bot.id:
        new_status = chat_member.new_chat_member.status
        
        if new_status in ("member", "administrator"):
            await add_group(chat_id, chat_title)
            logger.info(f"Guruh saqlandi: {chat_id} {chat_title}")
        elif new_status in ("left", "kicked"):
            await remove_group(chat_id)
            logger.info(f"Guruh o'chirildi: {chat_id}")




async def post_init(application):
    # Ma'lumotlar bazasini ishga tushirish
    init_db()
    
    # Bot ishga tushganda telethon klientini ulash
    # Bot ishga tushganda telethon klientini ulash
    try:
        is_authorized = await telethon_client.connect() # Telethon connection reinstated
        
        if not is_authorized:
            print("\n" + "="*50)
            print("TELETHON AVTORIZATSIYASI TALAB QILINADI")
            print("="*50)
            
            # Kodni so'rash (blocking input, lekin startup paytida bu muammo emas)
            # Async muhitda input() ishlatish uchun run_in_executor dan foydalanamiz
            import asyncio
            loop = asyncio.get_running_loop()
            code = await loop.run_in_executor(None, input, "Telegramga kelgan kodni kiriting: ")
            
            verification_result = await telethon_client.verify_code(code)
            
            if verification_result == True:
                logger.info("Telethon client muvaffaqiyatli ulandi va avtorizatsiyadan o'tdi")
            elif verification_result == "password_required":
                print("\n" + "="*50)
                print("IKKI BOSQICHLI TEKSHIRUV (2FA) PAROLI TALAB QILINADI")
                print("="*50)
                password = await loop.run_in_executor(None, input, "Telegram parolini kiriting: ")
                
                if await telethon_client.verify_password(password):
                    logger.info("Telethon client muvaffaqiyatli ulandi va avtorizatsiyadan o'tdi")
                else:
                    logger.error("Noto'g'ri parol kiritildi!")
            else:
                logger.error("Noto'g'ri kod kiritildi yoki avtorizatsiya xatoligi!")
                # Dasturni to'xtatish yoki davom ettirish? 
                # Hozircha log yozib davom etamiz, lekin funksionallik cheklangan bo'ladi
        else:
            logger.info("Telethon client muvaffaqiyatli ulandi")
        
        # Persistent menu tugmalarini o'rnatish
        await set_bot_commands(application)
        logger.info("Persistent bot commands set.")

        # Bot description ni o'rnatish
        description_text = """🚀 @logi_peek_bot — yuk topish uchun aqlli yordamchi!

Bu bot sizga logistika ishlarini tez, qulay va ishonchli bajarishda yordam beradi:

🔍 Tez yuk qidirish
— Kerakli yuklarni bir necha soniyada toping

👥 Kontakt va guruhlar bilan ishlash
— Yuk egalari va haydovchilar bilan to‘g‘ridan-to‘g‘ri aloqa

💰 Balansni boshqarish
— Balansni tekshirish va oson to‘ldirish

👉 Botni ishga tushirish uchun Boshlash tugmasini bosing."""
        
        try:
            # Default (til tanlanmagan yoki boshqa tillar uchun)
            await application.bot.set_my_description(description_text)
            
            # Aniq tillar uchun ham o'rnatish
            await application.bot.set_my_description(description_text, language_code='uz')
            await application.bot.set_my_description(description_text, language_code='ru')
            await application.bot.set_my_description(description_text, language_code='en')
            
            logger.info("Bot description set successfully for multiple languages.")
        except Exception as e:
            logger.error(f"Failed to set bot description: {e}")

    except Exception as e:
        logger.error(f"Bot initialization error: {e}")

async def post_shutdown(application):
    # Bot to'xtaganda telethon klientini va DB ulanishini uzish
    await telethon_client.disconnect()
    # groups.db ulanishini yopish
    # if conn: # Global ulanish olib tashlandi
    #     conn.close() # Global ulanish olib tashlandi
    logger.info("Telethon client uzildi")

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        return
    
    # Botni yaratish
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    
    # Error handler
    async def error_handler(update, context):
        logger.error(f"Error: {context.error}", exc_info=context.error)
        if isinstance(context.error, telegram.error.Conflict):
            logger.warning("Conflict error: Another bot instance might be running. Please ensure only one instance is active.")

    application.add_error_handler(error_handler)
    
    # DEBUG: Chat ID larni logga chiqarish (Support guruhini topish uchun)
    async def log_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat:
            logger.info(f"--- DEBUG CHAT ID --- | Title: {update.effective_chat.title} | ID: {update.effective_chat.id} | Type: {update.effective_chat.type}")
    
    application.add_handler(MessageHandler(filters.ALL, log_chat_id), group=-1) 
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get_id", lambda u, c: u.message.reply_text(f"Bu chat ID raqami: {u.effective_chat.id}")))
    application.add_handler(get_language_conversation_handler()) # Til tanlash eng ustiga o'tkazildi
    
    application.add_handler(CommandHandler("balance", check_balance))
    application.add_handler(get_search_conversation_handler())
    # Search sahifa o'zgartirish va natijani ko'rish uchun callback query handler
    from search_handler import handle_search_page_callback
    application.add_handler(CallbackQueryHandler(handle_search_page_callback, pattern="^search_"))
    application.add_handler(get_group_conversation_handler())
    application.add_handler(get_contact_conversation_handler())

    application.add_handler(get_admin_conversation_handler())
    application.add_handler(get_broadcast_conversation_handler())
    application.add_handler(get_feedback_conversation_handler())
    application.add_handler(get_help_conversation_handler())
    
    # Faqat SUPPORT_GROUP_ID dan va reply bo'lgan xabarlar uchun
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=SUPPORT_GROUP_ID) & filters.REPLY & filters.TEXT & ~filters.COMMAND, 
        handle_admin_reply
    ))
    
    application.add_handler(ChatMemberHandler(on_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

    
    # Til tanlash uchun yangi CommandHandler
    # application.add_handler(CommandHandler("language", start_language_selection))
    
    # Balans tekshirish uchun handler
    balance_button_uz = get_message({'language': 'uz'}, "check_balance")
    balance_button_ru = get_message({'language': 'ru'}, "check_balance")
    balance_button_en = get_message({'language': 'en'}, "check_balance")
    application.add_handler(MessageHandler(filters.Regex(f"^({balance_button_uz}|{balance_button_ru}|{balance_button_en})$"), check_balance))
    
    # Statistika tugmasi olib tashlandi

    # Yordam tugmasi uchun handler (endi help_handler orqali ishlaydi)
    # help_button_uz = get_message({'language': 'uz'}, "help_button")
    # help_button_ru = get_message({'language': 'ru'}, "help_button")
    # help_button_en = get_message({'language': 'en'}, "help_button")
    # application.add_handler(MessageHandler(filters.Regex(f"^({help_button_uz}|{help_button_ru}|{help_button_en})$"), help_command))
    # application.add_handler(MessageHandler(filters.Regex(f"^({get_message({}, 'select_language_button', lang='uz')}|{get_message({}, 'select_language_button', lang='ru')})$"), start_language_selection))
    
    # Botni ishga tushirish
    application.run_polling(poll_interval=5)

if __name__ == '__main__':
    main()