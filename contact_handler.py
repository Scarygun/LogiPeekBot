import logging
import re
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler
from database import add_contact # database modulini import qilamiz
from language_handler import get_message
from keyboards import get_main_menu_keyboard, get_back_keyboard
from config import TEXTUP_EMAIL, TEXTUP_PASSWORD
from textup_client import TextUpClient, TextUpAPIError, TextUpAuthError

logger = logging.getLogger(__name__)

# Kontakt qo'shish holatlari
class ContactStates:
    WAITING_CONTACT = 1

# Kontakt qo'shishni boshlash
async def start_add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        get_message(context.user_data, "contact_add_start"),
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    return ContactStates.WAITING_CONTACT

# Kontakt ma'lumotlarini qayta ishlash
async def process_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import re
    text = update.message.text.strip()
    from language_handler import is_back_button
    if is_back_button(text):
        # Bosh menyuga qaytish
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await update.message.reply_text(
            get_message(context.user_data, "main_menu"),
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    contact_info = text
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
        
        # SMS yuborish logikasi
        if re.match(phone_pattern, cleaned_phone):
            try:
                client = TextUpClient(TEXTUP_EMAIL, TEXTUP_PASSWORD)
                tpl_data = await client.get_templates()
                templates = tpl_data.get("templates", [])
                active_tpl = [t for t in templates if t.get("status") in ("active", "approved", "in_verify")]
                
                if active_tpl:
                    # Birinchi tasdiqlangan shablonni olamiz
                    template = active_tpl[0]
                    sms_id = await client.send_sms(
                        template_id=template["id"],
                        message=template.get("content", ""),
                        recipients=[contact_phone_number]
                    )
                    logger.info("Avtomatik SMS yuborildi: %s", sms_id)
                    # Qo'shimcha xabar
                    await update.message.reply_text("✅ Taklifnoma SMS xabari yuborildi.")
                else:
                    logger.warning("SMS yuborish uchun faol shablon topilmadi.")
            except (TextUpAuthError, TextUpAPIError) as e:
                logger.error("Avtomatik SMS yuborishda xatolik: %s", e)
    else:
        await update.message.reply_text(
            get_message(context.user_data, "contact_add_error"),
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END

def get_contact_conversation_handler():
    from keyboards import get_all_menu_buttons
    all_buttons = get_all_menu_buttons(get_message)
    btn_pattern = "|".join([re.escape(b) for b in all_buttons])
    buttons_regex = f"^({btn_pattern})$"
    
    from language_handler import MESSAGES
    entry_buttons = [MESSAGES[lang]["add_contact"] for lang in MESSAGES]
    
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(entry_buttons), start_add_contact),
            CommandHandler("add_contact", start_add_contact)
        ],
        states={
            ContactStates.WAITING_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), process_contact)],
        },
        fallbacks=[]
    )