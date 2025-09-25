import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from search_handler import get_search_conversation_handler
from group_handler import get_group_conversation_handler
from contact_handler import get_contact_conversation_handler
from admin_handler import get_admin_conversation_handler
from telethon_client import telethon_client
from feedback_handler import get_feedback_conversation_handler
from database import init_db
from config import BOT_TOKEN # TELEGRAM_API_ID, TELEGRAM_API_HASH importini olib tashlaymiz
from config import USER_API_ID, USER_API_HASH
from menu import set_bot_commands
from language_handler import get_message, get_language_conversation_handler, LanguageStates, start_language_selection
from broadcast_handler import get_broadcast_conversation_handler # Yangi import
from keyboards import get_main_menu_keyboard # Yangi import


# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

async def start(update, context):
    # Start komandasi
    user_id = update.effective_user.id
    user_language = context.user_data.get('language', 'uz') # Default til 'uz'
    
    if not user_language:
        return await start_language_selection(update, context)
    
    reply_markup = get_main_menu_keyboard(context.user_data, get_message)

    await update.message.reply_text(
        f"{get_message(context.user_data, "bot_description_title")}\n\n"
        f"{get_message(context.user_data, "bot_description_line1")}\n"
        f"{get_message(context.user_data, "bot_username")} {get_message(context.user_data, "welcome").split('!')[0]}!\n"
        f"\n"
        f"{get_message(context.user_data, "bot_description_line2_8d")}\n"
        f"{get_message(context.user_data, "bot_description_line3_concert")}\n"
        f"{get_message(context.user_data, "bot_description_line4_slowed")}\n"
        f"\n"
        f"{get_message(context.user_data, "bot_description_line5_all_in_seconds")} - {get_message(context.user_data, "bot_username")}",
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
        parse_mode="Markdown"
    )

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
    logger.info("Telethon client uzildi")

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        return
    
    # Botni yaratish
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", check_balance))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(get_search_conversation_handler())
    application.add_handler(get_group_conversation_handler())
    application.add_handler(get_contact_conversation_handler())
    application.add_handler(get_admin_conversation_handler())
    application.add_handler(get_feedback_conversation_handler())
    application.add_handler(get_language_conversation_handler())
    application.add_handler(get_broadcast_conversation_handler()) # Yangi handler qo'shish
    
    # Til tanlash uchun yangi CommandHandler
    # application.add_handler(CommandHandler("language", start_language_selection))
    
    # Balans tekshirish uchun handler
    application.add_handler(MessageHandler(filters.Regex(get_message({}, "check_balance")), check_balance))
    # application.add_handler(MessageHandler(filters.Regex(f"^({get_message({}, 'select_language_button', lang='uz')}|{get_message({}, 'select_language_button', lang='ru')})$"), start_language_selection))
    
    # Botni ishga tushirish
    application.run_polling()

if __name__ == '__main__':
    main()