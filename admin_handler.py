import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
from config import ADMINS
from database import get_all_groups, get_all_contacts, get_group_count, get_contact_count, log_admin_action, get_all_feedback, get_user_count_from_json, get_group_count_from_json, get_contact_count_from_json, load_contacts_from_json # Yangilangan importlar
from language_handler import get_message
from keyboards import get_main_menu_keyboard
import re # Yangi import
from broadcast_handler import start_broadcast, BroadcastStates # Yangi import

logger = logging.getLogger(__name__)

def get_admin_main_menu_keyboard():
    # Admin paneli uchun faqat O'zbek tilidagi tugmalar
    user_data_uz = {'language': 'uz'}
    keyboard = [
        [get_message(user_data_uz, "stats_button"), get_message(user_data_uz, "groups_button")],
        [get_message(user_data_uz, "contacts_button"), get_message(user_data_uz, "add_balance_button")],
        [get_message(user_data_uz, "close_button")],
        [get_message(user_data_uz, "feedback_list_button")],
        [get_message(user_data_uz, "broadcast_message_button")]
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
    await update.message.reply_text(get_message({'language': 'uz'}, "admin_panel_welcome"), reply_markup=reply_markup, parse_mode="Markdown")
    
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
    stats_btn_text = get_message(user_data_uz, "stats_button").strip()
    groups_btn_text = get_message(user_data_uz, "groups_button").strip()
    contacts_btn_text = get_message(user_data_uz, "contacts_button").strip()
    add_balance_btn_text = get_message(user_data_uz, "add_balance_button").strip()
    close_btn_text = get_message(user_data_uz, "close_button").strip()
    feedback_list_btn_text = get_message(user_data_uz, "feedback_list_button").strip()
    broadcast_message_btn_text = get_message(user_data_uz, "broadcast_message_button").strip()
    
    logger.debug(f"Expected Stats Button: '{stats_btn_text}'")
    logger.debug(f"Expected Groups Button: '{groups_btn_text}'")
    logger.debug(f"Expected Contacts Button: '{contacts_btn_text}'")
    logger.debug(f"Expected Add Balance Button: '{add_balance_btn_text}'")
    logger.debug(f"Expected Close Button: '{close_btn_text}'")
    logger.debug(f"Expected Feedback List Button: '{feedback_list_btn_text}'")
    logger.debug(f"Expected Broadcast Message Button: '{broadcast_message_btn_text}'")
    logger.debug(f"Received Message Text: '{message_text}' (length: {len(message_text)})")
    
    if not is_admin(user_id):
        logger.warning(f"Admin bo'lmagan foydalanuvchi ({user_id}) admin tugmasini bosdi.")
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        return ConversationHandler.END
    
    try:
        # Matnlarni to'g'ri taqqoslash
        if message_text == stats_btn_text:
            logger.debug(f"Admin stats tugmasi bosildi. User ID: {user_id}")
            group_count = await get_group_count_from_json() # JSON faylidan guruhlar sonini olish
            contact_count = await get_contact_count_from_json() # JSON faylidan kontaktlar sonini olish
            
            total_users_json = await get_user_count_from_json() # JSON faylidan foydalanuvchilar sonini olish
            
            await update.message.reply_text(
                get_message(user_data_uz, "bot_stats_title") + "\n\n" +
                get_message(user_data_uz, "total_bot_users", count=total_users_json) + "\n" +
                get_message(user_data_uz, "group_count", count=group_count) + "\n" +
                get_message(user_data_uz, "contact_count", count=contact_count) + "\n" +
                get_message(user_data_uz, "last_update"),
                parse_mode="Markdown"
            )
            await log_admin_action(user_id, "view_stats", "system", "none")
            return AdminStates.MAIN_MENU
            
        elif message_text == groups_btn_text:
            logger.debug(f"Admin groups tugmasi bosildi. User ID: {user_id}")
            groups = await get_all_groups()
            if not groups:
                await update.message.reply_text(get_message(user_data_uz, "no_groups_found"))
                logger.debug(f"Guruhlar topilmadi. Admin ID: {user_id}")
                return AdminStates.MAIN_MENU
            
            from telegram.helpers import escape_markdown
            
            # Telegram xabar maksimal uzunligi 4096 belgi
            MAX_MESSAGE_LENGTH = 3000  # Xavfsizlik uchun biroz kamroq (escape qilingan matnlar uzunroq bo'lishi mumkin)
            MAX_GROUPS_TO_SHOW = 50  # Maksimal ko'rsatiladigan guruhlar soni
            
            # Sarlavhani escape qilamiz
            all_groups_title = escape_markdown(get_message(user_data_uz, "all_groups_title"), version=2)
            groups_text = all_groups_title + "\n\n"
            groups_shown = 0
            total_groups = len(groups)
            
            # Birinchi xabarni yuborish funksiyasi
            async def send_current_message():
                nonlocal groups_text
                if groups_text.strip() and groups_text.strip() != all_groups_title + "\n\n":
                    try:
                        # Xabar uzunligini tekshiramiz
                        if len(groups_text) > 4096:
                            # Xabarni qisqartiramiz
                            groups_text = groups_text[:4000] + "\n\n... (xabar juda uzun, qisqartirildi)"
                        await update.message.reply_text(groups_text, parse_mode="MarkdownV2")
                        groups_text = ""  # Xabarni yuborilgandan keyin tozalaymiz
                    except Exception as e:
                        logger.error(f"Xabar yuborishda xatolik: {e}")
                        # Xabar juda uzun bo'lsa, uni qisqartiramiz
                        if "too long" in str(e).lower():
                            # Xabarni yarmiga qisqartiramiz
                            half_length = len(groups_text) // 2
                            groups_text = groups_text[:half_length] + "\n\n... (xabar juda uzun, qisqartirildi)"
                            try:
                                await update.message.reply_text(groups_text, parse_mode="MarkdownV2")
                                groups_text = ""
                            except:
                                pass
            
            for idx, group in enumerate(groups):
                # Maksimal ko'rsatiladigan guruhlar sonini tekshiramiz
                if groups_shown >= MAX_GROUPS_TO_SHOW:
                    break
                
                # sqlite3.Row obyekti .get() metodiga ega emas, shuning uchun to'g'ridan-to'g'ri indekslash ishlatamiz
                try:
                    group_id = str(group['group_id'])
                    # None tekshiruvi - agar None bo'lsa, default qiymat ishlatamiz
                    group_name = str(group['group_name']) if group['group_name'] is not None else "Noma'lum"
                    added_date = str(group['added_date']) if group['added_date'] is not None else "Noma'lum"
                except (KeyError, IndexError, TypeError) as e:
                    logger.warning(f"Guruh ma'lumotlarini olishda xatolik: {e}")
                    # Fallback qiymatlar
                    try:
                        group_id = str(group['group_id']) if 'group_id' in group.keys() else "Noma'lum"
                    except:
                        group_id = "Noma'lum"
                    group_name = "Noma'lum"
                    added_date = "Noma'lum"
                
                # MarkdownV2 uchun maxsus belgilarni escape qilish
                group_id_escaped = escape_markdown(group_id, version=2)
                group_name_escaped = escape_markdown(group_name, version=2)
                added_date_escaped = escape_markdown(added_date, version=2)
                
                # Yangi qatorni yaratish
                new_line = f"🆔 {group_id_escaped}\n📛 {group_name_escaped}\n📅 {added_date_escaped}\n\n"
                
                # Agar yangi qator qo'shilsa, xabar juda uzun bo'lishini tekshiramiz
                if len(groups_text) + len(new_line) > MAX_MESSAGE_LENGTH:
                    # Joriy xabarni yuboramiz
                    await send_current_message()
                    
                    # Yangi xabarni boshlaymiz (MarkdownV2 uchun "davomi" ni escape qilamiz)
                    continuation_text = escape_markdown(" (davomi)", version=2)
                    groups_text = all_groups_title + continuation_text + "\n\n"
                
                groups_text += new_line
                groups_shown += 1
            
            # Qolgan guruhlar haqida ma'lumot
            if total_groups > groups_shown:
                more_text = get_message(user_data_uz, "more_groups", count=total_groups-groups_shown)
                more_text_escaped = escape_markdown(more_text, version=2)
                if len(groups_text) + len(more_text_escaped) > MAX_MESSAGE_LENGTH:
                    # Joriy xabarni yuboramiz
                    await send_current_message()
                    groups_text = ""
                groups_text += more_text_escaped
            
            # Oxirgi xabarni yuboramiz
            await send_current_message()
            
            await log_admin_action(user_id, "view_groups", "system", "none")
            logger.debug(f"Admin groups ma'lumotlari ko'rsatildi. Admin ID: {user_id}, Ko'rsatilgan: {groups_shown}/{total_groups}")
            return AdminStates.MAIN_MENU
            
        elif message_text == contacts_btn_text:
            logger.debug(f"Admin contacts tugmasi bosildi. User ID: {user_id}")
            # JSON fayldan kontaktlarni olish
            contacts_dict = await load_contacts_from_json()
            if not contacts_dict:
                await update.message.reply_text(get_message(user_data_uz, "no_contacts_found"))
                logger.debug(f"Kontaktlar topilmadi. Admin ID: {user_id}")
                return AdminStates.MAIN_MENU
            
            contacts_text = get_message(user_data_uz, "all_contacts_title") + "\n\n"
            contacts_list = list(contacts_dict.items())[:10]  # Faqat birinchi 10 tasini ko'rsatamiz
            
            for contact_key, contact_data in contacts_list:
                # Faqat telefon raqamini ko'rsatamiz
                phone_number = contact_data.get('phone_number', contact_key) if isinstance(contact_data, dict) else contact_key
                contacts_text += f"📞 {phone_number}\n\n"
            
            if len(contacts_dict) > 10:
                contacts_text += get_message(user_data_uz, "more_contacts", count=len(contacts_dict)-10)
            
            await update.message.reply_text(contacts_text, parse_mode="Markdown")
            await log_admin_action(user_id, "view_contacts", "system", "none")
            logger.debug(f"Admin contacts ma'lumotlari ko'rsatildi. Admin ID: {user_id}")
            
        elif message_text == add_balance_btn_text:
            logger.debug(f"Admin add_balance tugmasi bosildi. User ID: {user_id}")
            await update.message.reply_text(
                get_message(user_data_uz, "add_balance_title") + "\n\n" +
                get_message(user_data_uz, "add_balance_format"),
                parse_mode="Markdown"
            )
            logger.debug(f"Admin ADD_BALANCE holatiga o'tmoqda. Admin ID: {user_id}")
            return AdminStates.ADD_BALANCE
            
        elif message_text == close_btn_text:
            logger.debug(f"Admin close tugmasi bosildi. User ID: {user_id}")
            await update.message.reply_text(get_message(user_data_uz, "admin_panel_close"))
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
            
        elif message_text == broadcast_message_btn_text:
            logger.debug(f"Admin broadcast tugmasi bosildi. User ID: {user_id}. Broadcast suhbatini boshlamoqda.")
            return await start_broadcast(update, context)

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
def get_admin_conversation_handler():
    logger.debug("Admin ConversationHandler yaratilmoqda...")
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={
            AdminStates.MAIN_MENU: [
                MessageHandler(filters.Text([
                    get_message({'language': 'uz'}, "stats_button").strip(),
                    get_message({'language': 'uz'}, "groups_button").strip(),
                    get_message({'language': 'uz'}, "contacts_button").strip(),
                    get_message({'language': 'uz'}, "add_balance_button").strip(),
                    get_message({'language': 'uz'}, "close_button").strip(),
                    get_message({'language': 'uz'}, "feedback_list_button").strip(),
                    get_message({'language': 'uz'}, "broadcast_message_button").strip()
                ]), admin_message_handler)
            ],
            AdminStates.ADD_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance)],
        },
        fallbacks=[CommandHandler("admin", admin_panel)],
    )
