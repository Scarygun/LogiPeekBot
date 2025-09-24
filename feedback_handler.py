import os
from telegram import Update
from telegram.ext import ConversationHandler, MessageHandler, filters, ContextTypes
from database import save_feedback
from language_handler import get_message

# Feedback uchun maxsus holatlar
FEEDBACK_TEXT = 1

async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(get_message(context.user_data, "feedback_start"))
    return FEEDBACK_TEXT

async def feedback_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_feedback = update.message.text
    user_id = update.effective_user.id
    
    await save_feedback(user_id, user_feedback)
    
    await update.message.reply_text(get_message(context.user_data, "feedback_thanks"))
    return ConversationHandler.END

async def feedback_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(get_message(context.user_data, "feedback_cancelled"))
    return ConversationHandler.END

def get_feedback_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(get_message({}, "send_feedback")), feedback_start)],
        states={
            FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_received)]
        },
        fallbacks=[MessageHandler(filters.COMMAND, feedback_cancel)]
    )
