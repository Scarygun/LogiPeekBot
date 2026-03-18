import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import ADMINS
from config import ADMINS
from database import get_all_groups, get_all_contacts, get_group_count, get_contact_count, log_admin_action, get_all_feedback, get_user_count_from_json, get_group_count_from_json, get_contact_count_from_json, load_contacts_from_json, load_groups_from_json, load_users_from_json # Yangilangan importlar
from language_handler import get_message
from keyboards import get_main_menu_keyboard, get_back_keyboard
import re # Yangi import
from config import ADMINS
from datetime import datetime

import html # Yangi import
logger = logging.getLogger(__name__)

def get_admin_main_menu_keyboard():
    # Admin paneli uchun faqat O'zbek tilidagi tugmalar
    user_data_uz = {'language': 'uz'}
    keyboard = [
        [get_message(user_data_uz, "groups_button"), get_message(user_data_uz, "contacts_button")],
        [get_message(user_data_uz, "add_balance_button"), get_message(user_data_uz, "feedback_list_button")],
        [get_message(user_data_uz, "users_count_button")],
        [get_message(user_data_uz, "back_button")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

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
    
    reply_markup = get_admin_main_menu_keyboard() # Faqat O'zbek tilida
    
    # HTML taglarni olib tashlaymiz va Markdown bold qilamiz
    welcome_msg = get_message({'language': 'uz'}, "admin_panel_welcome").replace("<b>", "").replace("</b>", "")
    # "Admin-panel" qismini bold qilish
    if "Admin-panel" in welcome_msg:
        welcome_msg = welcome_msg.replace("Admin-panel", "*Admin-panel*")
    elif "Admin panel" in welcome_msg: # O'zbekcha variant
        welcome_msg = welcome_msg.replace("Admin panel", "*Admin panel*")
        
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")
    
    await log_admin_action(user_id, "open_admin_panel", "system", "none")
    logger.debug(f"Admin panel MAIN_MENU holatiga qaytmoqda. User ID: {user_id}. Return state: {AdminStates.MAIN_MENU}")
    return AdminStates.MAIN_MENU

# Admin tugmalarini qayta ishlash
async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip() if update.message.text else ""
    logger.info(f"Admin message handler ishga tushdi. User ID: {user_id}, Message Text: '{message_text}'")
    
    user_data_uz = {'language': 'uz'}
    
    # Har bir tugma matnini logga chiqarish

    groups_btn_text = get_message(user_data_uz, "groups_button").strip()
    contacts_btn_text = get_message(user_data_uz, "contacts_button").strip()
    add_balance_btn_text = get_message(user_data_uz, "add_balance_button").strip()
    close_btn_text = get_message(user_data_uz, "close_button").strip()
    feedback_list_btn_text = get_message(user_data_uz, "feedback_list_button").strip()
    users_count_btn_text = get_message(user_data_uz, "users_count_button").strip()
    

    logger.debug(f"Expected Groups Button: '{groups_btn_text}'")
    logger.debug(f"Expected Contacts Button: '{contacts_btn_text}'")
    logger.debug(f"Expected Add Balance Button: '{add_balance_btn_text}'")
    logger.debug(f"Expected Close Button: '{close_btn_text}'")
    logger.debug(f"Expected Feedback List Button: '{feedback_list_btn_text}'")

    logger.debug(f"Received Message Text: '{message_text}' (length: {len(message_text)})")
    
    if not is_admin(user_id):
        logger.warning(f"Admin bo'lmagan foydalanuvchi ({user_id}) admin tugmasini bosdi.")
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        return ConversationHandler.END
    
    try:
        # Matnlarni to'g'ri taqqoslash
        if message_text == groups_btn_text:
            logger.debug(f"Admin groups tugmasi bosildi. User ID: {user_id}")
            groups = await load_groups_from_json()
            if not groups:
                await update.message.reply_text(get_message(user_data_uz, "no_groups_found"))
                logger.debug(f"Guruhlar topilmadi. Admin ID: {user_id}")
                return AdminStates.MAIN_MENU
            
            # Guruhlar ro'yxatini context da saqlaymiz
            context.user_data['admin_groups'] = groups
            
            # Birinchi sahifani ko'rsatamiz
            await show_admin_groups(update, context, page=0)
            
            await log_admin_action(user_id, "view_groups", "system", "none")
            return AdminStates.MAIN_MENU
            
        elif message_text == contacts_btn_text:
            logger.debug(f"Admin contacts tugmasi bosildi. User ID: {user_id}")
            # JSON fayldan kontaktlarni olish
            contacts_dict = await load_contacts_from_json()
            if not contacts_dict:
                await update.message.reply_text(get_message(user_data_uz, "no_contacts_found"))
                logger.debug(f"Kontaktlar topilmadi. Admin ID: {user_id}")
                return AdminStates.MAIN_MENU
            
            # Kontaktlarni context da saqlaymiz
            context.user_data['admin_contacts'] = contacts_dict
            
            # Birinchi sahifani ko'rsatamiz
            await show_admin_contacts(update, context, page=0)
            
            await log_admin_action(user_id, "view_contacts", "system", "none")
            logger.debug(f"Admin contacts ma'lumotlari ko'rsatildi. Admin ID: {user_id}")
            
        elif message_text == add_balance_btn_text:
            logger.debug(f"Admin add_balance tugmasi bosildi. User ID: {user_id}")
            reply_markup = get_back_keyboard(user_data_uz, get_message)
            await update.message.reply_text(
                get_message(user_data_uz, "add_balance_title") + "\n\n" +
                get_message(user_data_uz, "add_balance_format"),
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            logger.debug(f"Admin ADD_BALANCE holatiga o'tmoqda. Admin ID: {user_id}")
            return AdminStates.ADD_BALANCE
            
        elif message_text == close_btn_text or message_text == get_message(user_data_uz, "back_button").strip():
            logger.debug(f"Admin close/back tugmasi bosildi. User ID: {user_id}")
            # await update.message.reply_text(get_message(user_data_uz, "admin_panel_close")) # "Yopildi" xabari shart emas, chunki menyu chiqadi
            await log_admin_action(user_id, "close_admin_panel", "system", "none")
            
            # Asosiy menyuga qaytish
            user_language = context.user_data.get('language', 'uz')
            main_menu_markup = get_main_menu_keyboard({'language': user_language}, get_message)
            await update.message.reply_text(get_message({'language': user_language}, "main_menu"), reply_markup=main_menu_markup)
            
            logger.debug(f"Admin panel yopildi. Asosiy menyuga qaytmoqda. Admin ID: {user_id}")
            return ConversationHandler.END
            
        elif message_text == feedback_list_btn_text:
            logger.debug(f"Admin feedback list tugmasi bosildi. User ID: {user_id}")
            feedback_list = await get_all_feedback()
            
            if not feedback_list:
                await update.message.reply_text(get_message(user_data_uz, "no_feedback_yet"))
                return AdminStates.MAIN_MENU
            
            message_text = get_message(user_data_uz, "feedback_list_title") + "\n\n"
            for i, feedback in enumerate(feedback_list):
                message_text += f"{i+1}. User ID: {feedback['user_id']}\n   Fikr: {feedback['feedback_text']}\n   Vaqt: {feedback['timestamp']}\n\n"
            
            await update.message.reply_text(message_text, parse_mode="Markdown")
            return AdminStates.MAIN_MENU
            
        elif message_text == users_count_btn_text:
            logger.debug(f"Admin users count tugmasi bosildi. User ID: {user_id}")
            users = await load_users_from_json()
            contacts = await load_contacts_from_json()
            groups = await load_groups_from_json()
            
            users_count = len(users)
            contacts_count = len(contacts)
            groups_count = len(groups)
            
            # Xabar yuborish
            await update.message.reply_text(
                get_message(user_data_uz, "users_count_msg", 
                            users_count=users_count, 
                            contacts_count=contacts_count, 
                            groups_count=groups_count),
                parse_mode="HTML"
            )
                
            await log_admin_action(user_id, "view_users_count", "system", "none")
            return AdminStates.MAIN_MENU
            
            
        logger.warning(f"Noma'lum xabar ('{message_text}') admin panelda. User ID: {user_id}")
        return AdminStates.MAIN_MENU
    except Exception as e:
        logger.error(f"Admin message handlerda xatolik yuz berdi: {e}")
        await update.message.reply_text(get_message(user_data_uz, "admin_unexpected_error"))
        return ConversationHandler.END

# Balans qo'shish
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    logger.debug(f"add_balance funksiyasi ishga tushdi. User ID: {user_id}, Message Text: {message_text}")
    
    if not is_admin(user_id):
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        return ConversationHandler.END

    # Back button handling
    user_data_uz = {'language': 'uz'}
    back_text = get_message(user_data_uz, "back_button")
    
    if message_text == back_text:
        reply_markup = get_admin_main_menu_keyboard()
        await update.message.reply_text(
            get_message(user_data_uz, "admin_panel_welcome"),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return AdminStates.MAIN_MENU
    
    try:
        if ':' not in message_text:
            raise ValueError(get_message({'language': 'uz'}, "add_balance_wrong_format")) # The message is handled by the reply_text in except block
            
        user_id_to_add, amount = message_text.split(':', 1)
        user_id_to_add = user_id_to_add.strip()
        amount = float(amount.strip())
        
        # Bu yerda haqiqiy balans qo'shish logikasi bo'ladi
        # Hozircha faqat log yozamiz
        
        await log_admin_action(user_id, "add_balance", "user", user_id_to_add)
        
        await update.message.reply_text(
            get_message({'language': 'uz'}, "balance_added_success", user_id=user_id_to_add, amount=amount),
            parse_mode="Markdown"
        )
        logger.debug(f"Balans qo'shish muvaffaqiyatli. Admin ID: {user_id}, Target User ID: {user_id_to_add}, Amount: {amount}")
        
    except ValueError:
        logger.error(f"Balans qo'shishda noto'g'ri format. Admin ID: {user_id}, Message: {message_text}")
        await update.message.reply_text(
            get_message({'language': 'uz'}, "add_balance_wrong_format"),
            parse_mode="Markdown"
        )
        return AdminStates.ADD_BALANCE
    
    # Asosiy menyuga qaytish
    reply_markup = get_admin_main_menu_keyboard() # Faqat O'zbek tilida
    
    await update.message.reply_text(
        get_message({'language': 'uz'}, "admin_panel_welcome"),
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    logger.debug(f"Balans qo'shishdan so'ng MAIN_MENU ga qaytmoqda. Admin ID: {user_id}")
    return AdminStates.MAIN_MENU

# Admin conversation handler yaratish
async def show_admin_groups(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Guruhlarni sahifalab ko'rsatish"""
    # Xabarni o'chirishga harakat qilamiz (eski xabarni tozalash uchun)
    if update.callback_query:
        try:
            # Callback bo'lsa, xabarni tahrirlaymiz
            pass 
        except:
            pass
            
    user_id = update.effective_user.id
    groups = context.user_data.get('admin_groups', [])
    
    if not groups:
        return
    
    RESULTS_PER_PAGE = 10
    total_pages = (len(groups) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    start_idx = page * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, len(groups))
    page_groups = groups[start_idx:end_idx]
    
    # Header
    # "Jami topildi: {count} ta natija"
    header = f"Sahifa {page + 1} / {total_pages}\n\nJami topildi: {len(groups)} ta natija\n\n"
    
    # HTML uchun escape qilish shart emas, chunki biz o'zimiz html taglarini qo'shamiz
    # Lekin user inputini escape qilish kerak (hozircha user inputi yo'q, faqat json data)
    
    message_text = header
    
    # Ro'yxat
    for i, group_link in enumerate(page_groups):
        actual_idx = start_idx + i + 1
        group_link = str(group_link)
        
        # Linkni optimallashtirish: Native Telegram formatiga o'tish
        # Foydalanuvchi "shuni shunday kuchirib yuborish" dedi, ya'ni linkni ochiq ko'rinishda yozish
        # Bu eng ishonchli usul.
        
        display_text = ""
        
        # Agar oddiy username linki bo'lsa (joinchat yoki + bo'lmasa)
        if "t.me/" in group_link and "joinchat" not in group_link and "+" not in group_link:
            username_match = re.search(r't\.me/([a-zA-Z0-9_]+)', group_link)
            if username_match:
                username = username_match.group(1)
                display_text = f"@{username}"
            else:
                 display_text = group_link
        else:
            display_text = group_link
            
        # HTML taglarini escape qilish (xavfsizlik uchun)
        # Linkni o'zini escape qilmaymiz, chunki Telegram o'zi topadi (agar HTML parse_mode ishlatilmasa)
        # Lekin biz HTML ishlatayapmiz, shuning uchun biroz ehtiyot bo'lish kerak.
        # Agar parse_mode=HTML bo'lsa, @username va linklar avtomatik ishlamasligi mumkin agar <a> ichida bo'lmasa.
        # Lekin Telegram HTML mode da ham oddiy linklarni taniydi.
        
        # Eng ishonchli variant: <a href="link">@username</a> shaklida emas, shunchaki text.
        # Lekin biz HTML mode ishlatayapmiz.
        # Agar biz linkni ochiq yozsak: https://t.me/... Telegram buni link deb biladi.
        
        display_safe = html.escape(display_text)
        
        # Format: 1.) 🌍 @username | 🇺🇿 | LOGISTICA 🌍
        row_text = f"🌍 {display_safe} | 🇺🇿 | LOGISTICA 🌍"
        
        item_text = f"{actual_idx}.) {row_text}\n"
        message_text += item_text
        
    message_text += f"\n<i>{datetime.now().strftime('%H:%M')}</i>"

    # Tugmalar
    keyboard = []
    
    nav_row = []
    nav_row.append(InlineKeyboardButton("🏠 Bosh menyu", callback_data="admin_groups_menu"))
    
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin_groups_page_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin_groups_page_{page+1}"))
        
    keyboard.append(nav_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)

async def admin_groups_pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "admin_groups_menu":
        # Bosh menyuga qaytish
        # Xabarni o'chirish yoki tahrirlash
        try:
            await query.message.delete()
        except:
            pass
            
        # Yangi menyu xabarini yuborish
        reply_markup = get_admin_main_menu_keyboard()
        
        # HTML taglarni olib tashlaymiz va Markdown bold qilamiz
        welcome_msg = get_message({'language': 'uz'}, "admin_panel_welcome").replace("<b>", "").replace("</b>", "")
        if "Admin-panel" in welcome_msg:
             welcome_msg = welcome_msg.replace("Admin-panel", "*Admin-panel*")
        elif "Admin panel" in welcome_msg:
             welcome_msg = welcome_msg.replace("Admin panel", "*Admin panel*")
             
        await query.message.reply_text(
            welcome_msg,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return AdminStates.MAIN_MENU
        
    elif data.startswith("admin_groups_page_"):
        page = int(data.split("_")[-1])
        await show_admin_groups(update, context, page=page)
        return AdminStates.MAIN_MENU

async def show_admin_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Kontaktlarni sahifalab ko'rsatish"""
    # Xabarni o'chirishga harakat qilamiz (eski xabarni tozalash uchun)
    if update.callback_query:
        try:
            # Callback bo'lsa, xabarni tahrirlaymiz
            pass 
        except:
            pass
            
    user_id = update.effective_user.id
    
    # Kontaktlar dict formatida
    contacts_dict = context.user_data.get('admin_contacts', {})
    
    # Listga o'tkazish
    contacts_list = []
    if isinstance(contacts_dict, dict):
        for key, value in contacts_dict.items():
            phone = key
            if isinstance(value, dict):
                phone = value.get('phone_number', key)
            contacts_list.append(phone)
            
    if not contacts_list:
        return
    
    RESULTS_PER_PAGE = 10
    total_pages = (len(contacts_list) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    start_idx = page * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, len(contacts_list))
    page_contacts = contacts_list[start_idx:end_idx]
    
    # Header
    header = f"Sahifa {page + 1} / {total_pages}\n\nJami topildi: {len(contacts_list)} ta natija\n\n"
    
    message_text = header
    
    # Ro'yxat
    for i, contact in enumerate(page_contacts):
        actual_idx = start_idx + i + 1
        contact = str(contact)
        
        # Native format: shunchaki text
        # Format: 1. +998901234567
        item_text = f"{actual_idx}. {contact}\n"
        message_text += item_text
        
    message_text += f"\n{datetime.now().strftime('%H:%M')}"

    # Tugmalar
    keyboard = []
    
    nav_row = []
    nav_row.append(InlineKeyboardButton("🏠 Bosh menyu", callback_data="admin_contacts_menu"))
    
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin_contacts_page_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin_contacts_page_{page+1}"))
        
    keyboard.append(nav_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # parse_mode=None (Default)
    if update.callback_query:
        await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup, disable_web_page_preview=True)

async def admin_contacts_pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "admin_contacts_menu":
        # Bosh menyuga qaytish
        try:
            await query.message.delete()
        except:
            pass
            
        reply_markup = get_admin_main_menu_keyboard()
        # HTML taglarni olib tashlaymiz
        welcome_msg = get_message({'language': 'uz'}, "admin_panel_welcome").replace("<b>", "").replace("</b>", "")
        if "Admin-panel" in welcome_msg:
             welcome_msg = welcome_msg.replace("Admin-panel", "*Admin-panel*")
        elif "Admin panel" in welcome_msg:
             welcome_msg = welcome_msg.replace("Admin panel", "*Admin panel*")
             
        await query.message.reply_text(
            welcome_msg,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return AdminStates.MAIN_MENU
        
    elif data.startswith("admin_contacts_page_"):
        page = int(data.split("_")[-1])
        await show_admin_contacts(update, context, page=page)
        return AdminStates.MAIN_MENU

# Admin conversation handler yaratish
def get_admin_conversation_handler():
    logger.debug("Admin ConversationHandler yaratilmoqda...")
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={
            AdminStates.MAIN_MENU: [
                MessageHandler(filters.Text([
                    get_message({'language': 'uz'}, "groups_button").strip(),
                    get_message({'language': 'uz'}, "contacts_button").strip(),
                    get_message({'language': 'uz'}, "add_balance_button").strip(),
                    get_message({'language': 'uz'}, "close_button").strip(),
                    get_message({'language': 'uz'}, "back_button").strip(), # Added Back button
                    get_message({'language': 'uz'}, "feedback_list_button").strip(),
                    get_message({'language': 'uz'}, "users_count_button").strip()
                ]), admin_message_handler),
                CallbackQueryHandler(admin_groups_pagination_handler, pattern="^admin_groups_"),
                CallbackQueryHandler(admin_contacts_pagination_handler, pattern="^admin_contacts_")
            ],
            AdminStates.ADD_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance)],
        },
        fallbacks=[CommandHandler("admin", admin_panel)],
    )

