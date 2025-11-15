import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from database import add_contact # database modulini import qilamiz
from language_handler import get_message

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
    import re
    contact_info = update.message.text.strip()
    user_id = str(update.effective_user.id) # Kontakt qo'shayotgan foydalanuvchining ID si
    
    # Telefon raqamini ajratib olish
    contact_phone_number = contact_info
    contact_user_id = contact_info
    
    # Telefon raqamini tozalash va tekshirish
    # Telefon raqami formatlari: +998901234567, 998901234567, 901234567
    phone_pattern = r'^\+?998\d{9}$|^998\d{9}$|^\d{9}$'
    cleaned_phone = contact_info.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Agar telefon raqami formatida bo'lsa
    if re.match(phone_pattern, cleaned_phone):
        if cleaned_phone.startswith('998') and not cleaned_phone.startswith('+998'):
            contact_phone_number = '+' + cleaned_phone
        elif cleaned_phone.startswith('9'):
            contact_phone_number = '+998' + cleaned_phone
        else:
            contact_phone_number = cleaned_phone if cleaned_phone.startswith('+') else '+' + cleaned_phone
    else:
        # Agar telefon raqami emas bo'lsa, user_id sifatida ishlatamiz
        contact_phone_number = contact_info
        contact_user_id = contact_info

    # Faqat phone_number ni uzatamiz, username va full_name bo'sh
    if await add_contact(contact_user_id, None, None, contact_phone_number):
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

def get_contact_conversation_handler():
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f"^({get_message({'language': 'uz'}, 'add_contact')}|{get_message({'language': 'ru'}, 'add_contact')})$"), 
                start_add_contact
            )
        ],
        states={
            ContactStates.WAITING_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_contact)],
        },
        fallbacks=[]
    )