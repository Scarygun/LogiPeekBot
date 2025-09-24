import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler
from language_handler import get_message
from database import get_all_contacts, get_all_groups # Barcha foydalanuvchilar va guruhlarni olish uchun
from config import ADMINS

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Xabar tarqatish holatlari
class BroadcastStates:
    RECEIVE_MESSAGE = 1
    CONFIRM_BROADCAST = 2

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_user or not await is_admin(update.effective_user.id):
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        return ConversationHandler.END

    keyboard = [[get_message(context.user_data, "cancel_button")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(get_message(context.user_data, "broadcast_start_message"), reply_markup=reply_markup)
    return BroadcastStates.RECEIVE_MESSAGE

async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['broadcast_text'] = update.message.text
    keyboard = [
        [get_message(context.user_data, "confirm_button"), get_message(context.user_data, "cancel_button")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(get_message(context.user_data, "broadcast_confirm_message").format(message=update.message.text), reply_markup=reply_markup)
    return BroadcastStates.CONFIRM_BROADCAST

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == get_message(context.user_data, "confirm_button"):
        await send_broadcast(update, context)
        return ConversationHandler.END
    elif choice == get_message(context.user_data, "cancel_button"):
        await update.message.reply_text(get_message(context.user_data, "broadcast_cancelled"))
        return ConversationHandler.END
    else:
        await update.message.reply_text(get_message(context.user_data, "invalid_choice"))
        return BroadcastStates.CONFIRM_BROADCAST

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_to_send = context.user_data.get('broadcast_text')
    if not message_to_send:
        await update.message.reply_text(get_message(context.user_data, "broadcast_error"))
        return

    users = get_all_contacts() # Database'dan barcha foydalanuvchilarni olish
    groups = get_all_groups() # Database'dan barcha guruhlarni olish
    
    sent_count = 0
    failed_count = 0

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message_to_send)
            sent_count += 1
        except Exception as e:
            logger.error(f"Xabar {user_id} ga yuborishda xato: {e}")
            failed_count += 1

    for group_id in groups:
        try:
            await context.bot.send_message(chat_id=group_id, text=message_to_send)
            sent_count += 1
        except Exception as e:
            logger.error(f"Xabar {group_id} ga yuborishda xato: {e}")
            failed_count += 1

    await update.message.reply_text(get_message(context.user_data, "broadcast_success").format(sent=sent_count, failed=failed_count))

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(get_message(context.user_data, "broadcast_cancelled"))
    return ConversationHandler.END

def get_broadcast_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^({get_message({}, 'broadcast_message_button', lang='uz')}|{get_message({}, 'broadcast_message_button', lang='ru')})$"), start_broadcast)],
        states={
            BroadcastStates.RECEIVE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message)],
            BroadcastStates.CONFIRM_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_broadcast)]
        },
        fallbacks=[MessageHandler(filters.Regex(get_message({}, "cancel_button")), cancel_broadcast)]
    )

async def is_admin(user_id):
    return user_id in ADMINS
