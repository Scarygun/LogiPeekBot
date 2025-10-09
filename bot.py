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
from config import BOT_TOKEN, OWNER_ID # LOG_FILE_NAME endi alohida import qilinadi
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ChatMemberHandler # ChatMemberHandler Yangi import
import telegram # Added for telegram.error.Conflict
from search_handler import get_search_conversation_handler
from group_handler import get_group_conversation_handler
from contact_handler import get_contact_conversation_handler
from admin_handler import get_admin_conversation_handler
from telethon_client import telethon_client
from feedback_handler import get_feedback_conversation_handler
from database import init_db, add_group, remove_group, get_all_groups, add_user_to_json, get_user_count_from_json # Yangilangan importlar
from config import USER_API_ID, USER_API_HASH
from menu import set_bot_commands
from language_handler import get_message, get_language_conversation_handler, LanguageStates, start_language_selection
from broadcast_handler import get_broadcast_conversation_handler # Olib tashlandi
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
    await add_group(chat_id, title) # database.py dagi funksiyani chaqirish

async def remove_group(chat_id: int):
    await remove_group(chat_id) # database.py dagi funksiyani chaqirish

async def get_all_groups():
    return await get_all_groups() # database.py dagi funksiyani chaqirish

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
        f"{get_message(context.user_data, 'bot_description_title')}\n\n"
        f"{get_message(context.user_data, 'bot_description_line1')}\n"
        f"{get_message(context.user_data, 'bot_username')} {get_message(context.user_data, 'welcome').split('!')[0]}!\n"
        f"\n"
        f"{get_message(context.user_data, 'bot_description_line2_8d')}\n"
        f"{get_message(context.user_data, 'bot_description_line3_concert')}\n"
        f"{get_message(context.user_data, 'bot_description_line4_slowed')}\n"
        f"\n"
        f"{get_message(context.user_data, 'bot_description_line5_all_in_seconds')} - {get_message(context.user_data, 'bot_username')}",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def help_command(update, context):
    await update.message.reply_text(get_message(context.user_data, "help_message"))

async def stats_command(update, context):
    user_language = context.user_data.get('language', 'uz')
    
    total_users_json = await get_user_count_from_json() # JSON faylidan foydalanuvchilar sonini olish

    # Guruhlar sonini olish
    group_count = len(await get_all_groups()) if await get_all_groups() else 0

    # Kontaktlar sonini olish (agar tegishli funksiya mavjud bo'lsa, hozircha 0)
    contact_count = 0 # Hozircha nol, keyinchalik o'zgartirilishi mumkin

    # Statistik xabarini shakllantirish
    message_text = get_message(context.user_data, "bot_stats_title") + "\n\n"
    message_text += get_message(context.user_data, "total_bot_users", count=total_users_json) + "\n"
    message_text += get_message(context.user_data, "group_count", count=group_count) + "\n"
    message_text += get_message(context.user_data, "contact_count", count=contact_count) + "\n"
    message_text += get_message(context.user_data, "last_update")

    await update.message.reply_text(message_text, parse_mode="HTML")

async def check_balance(update, context):
    # Balans tekshirish funksiyasi
    await update.message.reply_text(
        get_message(context.user_data, "balance_check_title") + "\n\n" +
        get_message(context.user_data, "current_balance", balance=0) + "\n\n" +
        get_message(context.user_data, "contact_admin"),
        parse_mode="Markdown"
    )

async def on_chat_member_update(update, context):
    # Bu handler bot status o'zgarganda chaqiriladi (python-telegram-bot versiyasi)
    chat_member = update.chat_member
    chat_id = chat_member.chat.id
    chat_title = chat_member.chat.title
    
    # Botning o'zgarishini aniqlaymiz
    if chat_member.new_chat_member.user.id == context.bot.id:
        new_status = chat_member.new_chat_member.status
        
        if new_status in ("member", "administrator"):
            await add_group(chat_id, chat_title)
            logger.info(f"Guruh saqlandi: {chat_id} {chat_title}")
        elif new_status in ("left", "kicked"):
            await remove_group(chat_id)
            logger.info(f"Guruh o'chirildi: {chat_id}")

async def broadcast_command(update, context):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Sizda ruxsat yo'q.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Foydalanish: /broadcast XABAR matni")
        return

    text = " ".join(args)
    groups = await get_all_groups()
    sent = 0
    failed = 0
    for chat_id in groups:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Xato {chat_id}: {e}")
    await update.message.reply_text(f"Yuborildi: {sent}, xatoliklar: {failed}.")


async def post_init(application):
    # Ma'lumotlar bazasini ishga tushirish
    init_db()
    
    # Bot ishga tushganda telethon klientini ulash
    try:
        await telethon_client.connect() # Telethon connection reinstated
        logger.info("Telethon client muvaffaqiyatli ulandi")
        
        # Persistent menu tugmalarini o'rnatish
        await set_bot_commands(application)
        logger.info("Persistent bot commands set.")

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
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", check_balance))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command)) # Yangi handler qo'shish
    application.add_handler(get_search_conversation_handler())
    application.add_handler(get_group_conversation_handler())
    application.add_handler(get_contact_conversation_handler())
    application.add_handler(get_admin_conversation_handler())
    application.add_handler(get_feedback_conversation_handler())
    application.add_handler(get_language_conversation_handler())
    application.add_handler(ChatMemberHandler(on_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(get_broadcast_conversation_handler()) # Yangi handler qo'shish
    
    # Til tanlash uchun yangi CommandHandler
    # application.add_handler(CommandHandler("language", start_language_selection))
    
    # Balans tekshirish uchun handler
    balance_button_uz = get_message({'language': 'uz'}, "check_balance")
    balance_button_ru = get_message({'language': 'ru'}, "check_balance")
    application.add_handler(MessageHandler(filters.Regex(f"^({balance_button_uz}|{balance_button_ru})$"), check_balance))
    # application.add_handler(MessageHandler(filters.Regex(f"^({get_message({}, 'select_language_button', lang='uz')}|{get_message({}, 'select_language_button', lang='ru')})$"), start_language_selection))
    
    # Botni ishga tushirish
    application.run_polling(poll_interval=5)

if __name__ == '__main__':
    main()