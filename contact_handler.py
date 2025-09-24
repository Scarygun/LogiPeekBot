import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from database import add_contact # database modulini import qilamiz
from language_handler import get_message

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kontakt qo'shish holatlari
class ContactStates:
    WAITING_CONTACT = 1

# Kontakt qo'shishni boshlash
async def start_add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        get_message(context.user_data, "contact_add_start"),
        parse_mode="Markdown"
    )
    return ContactStates.WAITING_CONTACT

# Kontakt ma'lumotlarini qayta ishlash
async def process_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_info = update.message.text.strip()
    user_id = str(update.effective_user.id) # Kontakt qo'shayotgan foydalanuvchining ID si
    
    # Hozircha oddiy tahlil, keyinchalik murakkablashishi mumkin
    contact_user_id = contact_info # Qaysi foydalanuvchini qo'shayotganimizni bildiradi
    contact_username = contact_info
    contact_full_name = ""
    contact_phone_number = ""

    if await add_contact(contact_user_id, contact_username, contact_full_name, contact_phone_number):
        await update.message.reply_text(
            get_message(context.user_data, "contact_add_success", contact_info=contact_info),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            get_message(context.user_data, "contact_add_error"),
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END

# Bekor qilish
async def cancel_add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_message(context.user_data, "contact_add_cancelled"))
    return ConversationHandler.END

# Conversation handler yaratish
def get_contact_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(get_message({}, "add_contact")), start_add_contact)],
        states={
            ContactStates.WAITING_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_contact)],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^({get_message({}, 'cancel_button')}|Cancel)$"), cancel_add_contact)],
    )