import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
from config import ADMINS
from database import get_all_groups, get_all_contacts, get_group_count, get_contact_count, log_admin_action, get_all_feedback
from language_handler import get_message

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin panel holatlari
class AdminStates:
    MAIN_MENU = 1
    VIEW_GROUPS = 2
    VIEW_CONTACTS = 3
    ADD_BALANCE = 4
    VIEW_FEEDBACK = 5

# Admin ekanligini tekshirish
def is_admin(user_id):
    return user_id in ADMINS

# Admin panelni boshlash
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.debug(f"Admin panel buyrug'i ishga tushdi. User ID: {user_id}")
    
    if not is_admin(user_id):
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        logger.debug(f"Admin bo'lmagan foydalanuvchi ({user_id}) admin panelga kirishga urindi.")
        return ConversationHandler.END
    
    keyboard = [
        [get_message(context.user_data, "stats_button"), get_message(context.user_data, "groups_button")],
        [get_message(context.user_data, "contacts_button"), get_message(context.user_data, "add_balance_button")],
        [get_message(context.user_data, "close_button")]
        ,[get_message(context.user_data, "feedback_list_button")],
        [get_message(context.user_data, "broadcast_message_button")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(get_message(context.user_data, "admin_panel_welcome"), reply_markup=reply_markup, parse_mode="Markdown")
    
    await log_admin_action(user_id, "open_admin_panel", "system", "none")
    logger.debug(f"Admin panel MAIN_MENU holatiga qaytmoqda. User ID: {user_id}. Return state: {AdminStates.MAIN_MENU}")
    return AdminStates.MAIN_MENU

# Admin tugmalarini qayta ishlash
async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    logger.info(f"Admin message handler ishga tushdi. User ID: {user_id}, Message Text: {message_text}")
    
    if not is_admin(user_id):
        logger.warning(f"Admin bo'lmagan foydalanuvchi ({user_id}) admin tugmasini bosdi.")
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        return ConversationHandler.END
    
    try:
        if message_text == get_message(context.user_data, "stats_button"):
            logger.debug(f"Admin stats tugmasi bosildi. User ID: {user_id}")
            group_count = await get_group_count()
            contact_count = await get_contact_count()
            
            await update.message.reply_text(
                get_message(context.user_data, "bot_stats_title") + "\n\n" +
                get_message(context.user_data, "group_count", count=group_count) + "\n" +
                get_message(context.user_data, "contact_count", count=contact_count) + "\n" +
                get_message(context.user_data, "last_update"),
                parse_mode="Markdown"
            )
            await log_admin_action(user_id, "view_stats", "system", "none")
            
        elif message_text == get_message(context.user_data, "groups_button"):
            logger.debug(f"Admin groups tugmasi bosildi. User ID: {user_id}")
            groups = await get_all_groups()
            if not groups:
                await update.message.reply_text(get_message(context.user_data, "no_groups_found"))
                logger.debug(f"Guruhlar topilmadi. Admin ID: {user_id}")
                return AdminStates.MAIN_MENU
            
            groups_text = get_message(context.user_data, "all_groups_title") + "\n\n"
            for group in groups[:10]:  # Faqat birinchi 10 tasini ko'rsatamiz
                groups_text += f"🆔 {group[1]}\n📛 {group[2]}\n📅 {group[3]}\n\n"
            
            if len(groups) > 10:
                groups_text += get_message(context.user_data, "more_groups", count=len(groups)-10)
            
            await update.message.reply_text(groups_text, parse_mode="Markdown")
            await log_admin_action(user_id, "view_groups", "system", "none")
            logger.debug(f"Admin groups ma'lumotlari ko'rsatildi. Admin ID: {user_id}")
            
        elif message_text == get_message(context.user_data, "contacts_button"):
            logger.debug(f"Admin contacts tugmasi bosildi. User ID: {user_id}")
            contacts = await get_all_contacts()
            if not contacts:
                await update.message.reply_text(get_message(context.user_data, "no_contacts_found"))
                logger.debug(f"Kontaktlar topilmadi. Admin ID: {user_id}")
                return AdminStates.MAIN_MENU
            
            contacts_text = get_message(context.user_data, "all_contacts_title") + "\n\n"
            for contact in contacts[:10]:  # Faqat birinchi 10 tasini ko'rsatamiz
                contacts_text += f"🆔 {contact[1]}\n👤 {contact[3]}\n📞 {contact[4]}\n💰 {contact[5]} so'm\n\n"
            
            if len(contacts) > 10:
                contacts_text += get_message(context.user_data, "more_contacts", count=len(contacts)-10)
            
            await update.message.reply_text(contacts_text, parse_mode="Markdown")
            await log_admin_action(user_id, "view_contacts", "system", "none")
            logger.debug(f"Admin contacts ma'lumotlari ko'rsatildi. Admin ID: {user_id}")
            
        elif message_text == get_message(context.user_data, "add_balance_button"):
            logger.debug(f"Admin add_balance tugmasi bosildi. User ID: {user_id}")
            await update.message.reply_text(
                get_message(context.user_data, "add_balance_title") + "\n\n" +
                get_message(context.user_data, "add_balance_format"),
                parse_mode="Markdown"
            )
            logger.debug(f"Admin ADD_BALANCE holatiga o'tmoqda. Admin ID: {user_id}")
            return AdminStates.ADD_BALANCE
            
        elif message_text == get_message(context.user_data, "close_button"):
            logger.debug(f"Admin close tugmasi bosildi. User ID: {user_id}")
            await update.message.reply_text(get_message(context.user_data, "admin_panel_close"))
            await log_admin_action(user_id, "close_admin_panel", "system", "none")
            logger.debug(f"Admin panel yopildi. ConversationHandler.END qaytarilmoqda. Admin ID: {user_id}")
            return ConversationHandler.END
            
        elif message_text == get_message(context.user_data, "feedback_list_button"):
            logger.debug(f"Admin feedback list tugmasi bosildi. User ID: {user_id}")
            feedback_list = await get_all_feedback()
            
            if not feedback_list:
                await update.message.reply_text(get_message(context.user_data, "no_feedback_yet"))
                return AdminStates.MAIN_MENU
            
            message_text = get_message(context.user_data, "feedback_list_title") + "\n\n"
            for i, feedback in enumerate(feedback_list):
                message_text += f"{i+1}. User ID: {feedback['user_id']}\n   Fikr: {feedback['feedback_text']}\n   Vaqt: {feedback['timestamp']}\n\n"
            
            await update.message.reply_text(message_text, parse_mode="Markdown")
            return AdminStates.MAIN_MENU
            
        logger.warning(f"Noma'lum xabar ({message_text}) admin panelda. User ID: {user_id}")
        return AdminStates.MAIN_MENU
    except Exception as e:
        logger.error(f"Admin message handlerda xatolik yuz berdi: {e}")
        await update.message.reply_text(get_message(context.user_data, "admin_unexpected_error"))
        return ConversationHandler.END

# Balans qo'shish
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    logger.debug(f"add_balance funksiyasi ishga tushdi. User ID: {user_id}, Message Text: {message_text}")
    
    if not is_admin(user_id):
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        return ConversationHandler.END
    
    try:
        if ':' not in message_text:
            raise ValueError(get_message(context.user_data, "add_balance_wrong_format")) # The message is handled by the reply_text in except block
            
        user_id_to_add, amount = message_text.split(':', 1)
        user_id_to_add = user_id_to_add.strip()
        amount = float(amount.strip())
        
        # Bu yerda haqiqiy balans qo'shish logikasi bo'ladi
        # Hozircha faqat log yozamiz
        
        await log_admin_action(user_id, "add_balance", "user", user_id_to_add)
        
        await update.message.reply_text(
            get_message(context.user_data, "balance_added_success", user_id=user_id_to_add, amount=amount),
            parse_mode="Markdown"
        )
        logger.debug(f"Balans qo'shish muvaffaqiyatli. Admin ID: {user_id}, Target User ID: {user_id_to_add}, Amount: {amount}")
        
    except ValueError:
        logger.error(f"Balans qo'shishda noto'g'ri format. Admin ID: {user_id}, Message: {message_text}")
        await update.message.reply_text(
            get_message(context.user_data, "add_balance_wrong_format"),
            parse_mode="Markdown"
        )
        return AdminStates.ADD_BALANCE
    
    # Asosiy menyuga qaytish
    keyboard = [
        [get_message(context.user_data, "stats_button"), get_message(context.user_data, "groups_button")],
        [get_message(context.user_data, "contacts_button"), get_message(context.user_data, "add_balance_button")],
        [get_message(context.user_data, "close_button")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        get_message(context.user_data, "admin_panel_welcome"),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    logger.debug(f"Balans qo'shishdan so'ng MAIN_MENU ga qaytmoqda. Admin ID: {user_id}")
    return AdminStates.MAIN_MENU

# Admin conversation handler yaratish
def get_admin_conversation_handler():
    logger.debug("Admin ConversationHandler yaratilmoqda...")
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={
            AdminStates.MAIN_MENU: [
                MessageHandler(filters.Regex(f"^({get_message({}, 'stats_button')}|{get_message({}, 'groups_button')}|{get_message({}, 'contacts_button')}|{get_message({}, 'add_balance_button')}|{get_message({}, 'close_button')}|{get_message({}, 'feedback_list_button')}|{get_message({}, 'broadcast_message_button')})$"), admin_message_handler)
            ],
            AdminStates.ADD_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance)],
        },
        fallbacks=[CommandHandler("admin", admin_panel)],
    )
