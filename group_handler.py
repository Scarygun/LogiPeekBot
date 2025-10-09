import re
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from database import add_group
from language_handler import get_message
from telegram.helpers import escape_markdown

logger = logging.getLogger(__name__)

# Gruh qo'shish holatlari
class GroupStates:
    WAITING_GROUP = 1

# Gruh qo'shishni boshlash
async def start_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        get_message(context.user_data, "group_add_start"),
        parse_mode="Markdown"
    )
    return GroupStates.WAITING_GROUP

# Gruh ma'lumotlarini qayta ishlash
async def process_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_info = update.message.text.strip()
    
    # Guruh ma'lumotlarini tahlil qilish
    group_id = group_info
    group_name = group_info

    # Agar link bo'lsa, usernameni ajratib olish
    match = re.match(r'(?:https?://)?t.me/([a-zA-Z0-9_]+)', group_info)
    if match:
        group_id = match.group(1)
        group_name = match.group(1) # Guruh nomi ham username bo'lsin
    
    if await add_group(group_id, group_name):
        await update.message.reply_text(
            get_message(context.user_data, "group_add_success", group_name=escape_markdown(group_name, version=2)),
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
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f"^({get_message({'language': 'uz'}, 'add_group')}|{get_message({'language': 'ru'}, 'add_group')})$"), 
                start_add_group
            )
        ],
        states={
            GroupStates.WAITING_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_group)],
        },
        fallbacks=[]
    )