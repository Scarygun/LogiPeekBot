import os
from telegram import Update
from telegram.ext import ConversationHandler, MessageHandler, filters, ContextTypes, CommandHandler
from database import save_feedback
from language_handler import get_message
from keyboards import get_main_menu_keyboard, get_back_keyboard
import logging

logger = logging.getLogger(__name__)

# Feedback uchun maxsus holatlar
FEEDBACK_TEXT = 1

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        get_message(context.user_data, "feedback_start"),
        reply_markup=reply_markup
    )
    return FEEDBACK_TEXT

async def feedback_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_feedback = update.message.text
    back_text = get_message(context.user_data, "back_button")
    
    if user_feedback == back_text:
        # Bosh menyuga qaytish
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await update.message.reply_text(
            get_message(context.user_data, "main_menu"),
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    user_id = update.effective_user.id
    user_id = update.effective_user.id
    
    await save_feedback(user_id, user_feedback)
    
    await update.message.reply_text(get_message(context.user_data, "feedback_thanks"))
    return ConversationHandler.END

def get_feedback_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f"^({get_message({'language': 'uz'}, 'send_feedback')}|{get_message({'language': 'ru'}, 'send_feedback')})$"), 
                feedback_start
            ),
            CommandHandler("feedback", feedback_start)
        ],
        states={
            FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_received)]
        },
        fallbacks=[]
    )
