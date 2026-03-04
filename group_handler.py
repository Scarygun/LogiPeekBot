import re
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler
from database import add_group
from language_handler import get_message
from keyboards import get_main_menu_keyboard, get_back_keyboard
from telegram.helpers import escape_markdown

logger = logging.getLogger(__name__)

# Gruh qo'shish holatlari
class GroupStates:
    WAITING_GROUP = 1

# Gruh qo'shishni boshlash
async def start_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        get_message(context.user_data, "group_add_start"),
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    return GroupStates.WAITING_GROUP

# Gruh ma'lumotlarini qayta ishlash
async def process_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    back_text = get_message(context.user_data, "back_button")
    
    if text == back_text:
        # Bosh menyuga qaytish
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await update.message.reply_text(
            get_message(context.user_data, "main_menu"),
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    group_info = text
    
    # Guruh ma'lumotlarini tahlil qilish
    group_id = group_info
    group_name = group_info
    group_link = None
    username = None

    # Agar link bo'lsa, usernameni ajratib olish
    match = re.match(r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)', group_info)
    if match:
        username = match.group(1)
        group_id = username
        
        # To'liq linkni yaratish
        if group_info.startswith('http'):
            group_link = group_info
        else:
            group_link = f"https://t.me/{username}"
    else:
        # Agar link emas, balki username yoki ID bo'lsa
        # Telegram username formatini tekshirish
        if re.match(r'^[a-zA-Z0-9_]+$', group_info):
            # Bu username bo'lishi mumkin
            username = group_info
            group_link = f"https://t.me/{group_info}"
        else:
            # Bu ID bo'lishi mumkin, lekin link yaratib bo'lmaydi
            group_link = group_info
    
    # Telegram Bot API orqali guruhning haqiqiy nomini olish
    actual_group_title = None
    if username:
        try:
            # Bot API orqali guruh ma'lumotlarini olish
            chat = await context.bot.get_chat(f"@{username}")
            actual_group_title = chat.title
            logger.info(f"Guruhning haqiqiy nomi olingandi: {actual_group_title}")
        except Exception as e:
            logger.warning(f"Guruhning haqiqiy nomini olishda xatolik: {e}. Username ishlatilmoqda: {username}")
            actual_group_title = username
    elif group_link and not username:
        # ID bo'lsa, to'g'ridan-to'g'ri chaqirishga harakat qilamiz
        try:
            # ID ni int ga o'tkazishga harakat qilamiz
            chat_id_int = int(group_info)
            chat = await context.bot.get_chat(chat_id_int)
            actual_group_title = chat.title
            logger.info(f"Guruhning haqiqiy nomi (ID orqali) olingandi: {actual_group_title}")
        except Exception as e:
            logger.warning(f"Guruhning haqiqiy nomini (ID orqali) olishda xatolik: {e}")
            actual_group_title = group_info
    
    # Agar haqiqiy nom topilmagan bo'lsa, username yoki group_info ni ishlatamiz
    if not actual_group_title:
        actual_group_title = username or group_info
    
    # chat_id ni aniqlash (int yoki str bo'lishi mumkin)
    try:
        if isinstance(group_id, str) and group_id.isdigit():
            chat_id = int(group_id)
        else:
            chat_id = group_id
    except:
        chat_id = group_id
    
    # Guruhni qo'shish (JSON ga ham saqlash uchun linkni va haqiqiy nomni uzatamiz)
    if await add_group(chat_id, actual_group_title, group_link, username):
        await update.message.reply_text(
            get_message(context.user_data, "group_add_success", group_name=escape_markdown(actual_group_title, version=2)),
            parse_mode="MarkdownV2"
        )
    else:
        await update.message.reply_text(
            get_message(context.user_data, "group_add_error"),
            parse_mode="MarkdownV2"
        )
    
    return ConversationHandler.END

# Conversation handler yaratish
def get_group_conversation_handler():
    from keyboards import get_all_menu_buttons
    all_buttons = get_all_menu_buttons(get_message)
    btn_pattern = "|".join([re.escape(b) for b in all_buttons])
    buttons_regex = f"^({btn_pattern})$"
    
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f"^({get_message({'language': 'uz'}, 'add_group')}|{get_message({'language': 'ru'}, 'add_group')})$"), 
                start_add_group
            ),
            CommandHandler("add_group", start_add_group)
        ],
        states={
            GroupStates.WAITING_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), process_group)],
        },
        fallbacks=[]
    )