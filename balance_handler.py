import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from database import get_balance
from language_handler import get_message

logger = logging.getLogger(__name__)

async def handle_check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Check balance requested by user {user_id}")
    
    balance = await get_balance(user_id)
    
    await update.message.reply_text(
        get_message(context.user_data, "current_balance", balance=balance),
        parse_mode="HTML"
    )
    
    # Also show admin contact if balance is low or just as info
    await update.message.reply_text(
        get_message(context.user_data, "contact_admin"),
        parse_mode="HTML"
    )

def get_balance_handler():
    from language_handler import MESSAGES
    balance_buttons = [MESSAGES[lang]["check_balance"] for lang in MESSAGES]
    
    return MessageHandler(filters.Text(balance_buttons), handle_check_balance)
