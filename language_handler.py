import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler
from keyboards import get_main_menu_keyboard # Yangi import

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Til tanlash holatlari
class LanguageStates:
    SELECT_LANGUAGE = 1

# Barcha xabarlar lug'ati
MESSAGES = {
    "uz": {
        "welcome": "Salom! Yuk qidirish botiga xush kelibsiz.",
        "main_menu": "Quyidagi tugmalardan foydalaning:",
        "search_load": "🚛 Yuk qidirish",
        "add_group": "👥 Guruh qo'shish",
        "add_contact": "📞 Kontakt qo'shish",
        "check_balance": "💰 Balans tekshirish",
        "send_feedback": "✍️ Fikr bildirish",

        "balance_check_title": "💰 <b>Balans tekshirish</b>",
        "current_balance": "Hozirda sizning balansingiz: {balance} so'm",
        "contact_admin": "Balansingizni to'ldirish uchun admin bilan bog'laning: @Xx19_99",
        "language_selected": "Til muvaffaqiyatli o'rnatildi: O'zbekcha",
        "invalid_language": "Noto'g'ri til tanlovi. Iltimos, tugmalardan birini bosing.",
        "admin_panel_close": "✅ Admin panel yopildi",
        "admin_not_authorized": "❌ Siz admin emassiz!",
        "admin_panel_welcome": "👨‍💻 <b>Admin Panel</b>\n\nQuyidagi funksiyalardan foydalaning:",
        "groups_button": "👥 Guruhlar",
        "contacts_button": "📞 Kontaktlar",
        "add_balance_button": "💰 Balans qo'shish",
        "close_button": "❌ Yopish",
        "feedback_list_button": "Fikrlar ro'yxati",
        "no_groups_found": "❌ Guruhlar topilmadi!",
        "all_groups_title": "👥 <b>Barcha Guruhlar</b>",
        "more_groups": "📝 ... va yana {count} ta guruh",
        "no_contacts_found": "❌ Kontaktlar topilmadi!",
        "all_contacts_title": "📞 <b>Barcha Kontaktlar</b>",
        "more_contacts": "📝 ... va yana {count} ta kontakt",
        "add_balance_title": "💰 <b>Balans Qo'shish</b>",
        "add_balance_format": "Foydalanuvchi ID sini va miqdorni kiriting:\n\nFormat: `user_id:miqdor`\nMisol: `123456789:50000`",
        "feedback_list_title": "<b>Fikrlar ro'yxati:</b>",
        "no_feedback_yet": "Hali hech qanday fikr bildirilmagan.",
        "admin_unexpected_error": "❌ Admin panelda kutilmagan xato yuz berdi. Iltimos, keyinroq urinib ko'ring.",
        "add_balance_wrong_format": "❌ Noto'g'ri format!\n\nIltimos, quyidagi formatda kiriting:\n`user_id:miqdor`\n\nMisol: `123456789:50000`",
        "balance_added_success": "✅ Balans muvaffaqiyatli qo'shildi!\n\n👤 Foydalanuvchi ID: {user_id}\n💰 Miqdor: {amount} so'm",
        "contact_add_start": "📞 <b>Kontakt qo'shish</b>\n\nKontakt ma'lumotlarini yuboring (username yoki telefon raqam):",
        "contact_add_success": "✅ Kontakt muvaffaqiyatli qo'shildi:\n`{contact_info}`",
        "contact_add_error": "❌ Kontaktni qo'shishda xatolik yuz berdi yoki kontakt allaqachon mavjud.",
        "contact_add_cancelled": "Kontakt qo'shish bekor qilindi.",
        "feedback_start": "Fikringizni yozing. Biz uni yaxshilash uchun foydalanamiz.",
        "feedback_thanks": "Fikringiz uchun rahmat!",
        "feedback_cancelled": "Fikr bildirish bekor qilindi.",
        "group_add_start": "👥 <b>Guruh qo'shish</b>\n\nGuruh ID, username yoki linkini yuboring:",
        "group_add_success": "✅ Guruh muvaffaqiyatli qo'shildi:\n{group_name}",
        "group_add_error": "❌ Guruhni qo'shishda xatolik yuz berdi yoki guruh allaqachon mavjud.",
        "group_add_cancelled": "Guruh qo'shish bekor qilindi.",
        "search_error_telethon_not_connected": "❌ <b>Xato!</b>\n\nTelethon ulanmagan. Botni qayta ishga tushiring.\nAdmin bilan bog'laning: @Xx19_99",
        "search_from_city_prompt": "📍 <b>Qayerdan yuk qidiryapsiz?\n(Shahar nomini kiriting)</b>",
        "search_to_city_prompt": "📍 <b>Qayergacha kerak?\n(Maqsad shahrini kiriting)</b>",
        "search_in_progress": "🔍 <b>Qidiruv jarayoni</b>\n\n📍 {from_city} ➡️ {to_city}\n\n⏳ Guruhlardan qidirilmoqda...",
        "search_results_found": "✅ <b>{count} ta yuk topildi!</b>\n\n🔍 {from_city} ➡️ {to_city}",
        "search_more_results": "📝 Va yana {count} ta natija bor...",
        "search_no_results": "❌ <b>Yuk topilmadi</b>\n\n🔍 {from_city} ➡️ {to_city}\n\n<b>Ehtimoliy sabablar:</b>\n• Bu yo'nalishda yuk yo'q\n• Guruhlar yopiq yoki mavjud emas\n• So'nggi kunlarda faollik yo'q\n\n💡 Boshqa yo'nalishlarni sinab ko'ring",
        "search_error_unexpected": "❌ Qidiruv jarayonida xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
        "search_cancelled": "Qidiruv bekor qilindi.",
        "help_message": "Iltimos, @Xx19_99 ga yozing – biz sizga zudlik bilan yordam beramiz! 😊",
        "confirm_button": "Tasdiqlash",
        "invalid_choice": "Noto'g'ri tanlov. Iltimos, tugmalardan birini bosing.",
        "search_result_item": "<b>#{i} {group_title}</b>\n\n📅 {date} | 👤 {sender}\n\n💬 {text}{ellipsis}\n\n🔗 <a href='{link}'>Xabarni ko'rish</a>",
        "search_result_item_list": "{idx}.) 🌍 {title} | 🇺🇿 | LOGISTICA 🌍\n💬 {text}",
        "search_list_header": "Sahifa {page} / {total}\n\n📍 {from_city} ➡️ {to_city}\n\nJami topildi: {count} ta natija",
        "search_details_header": "<b>#{idx} {title}</b>\n\n📅 {date} | 👤 {sender}\n\n",
        "back_to_list": "🔙 Ro'yxatga qaytish",
        "main_menu_button": "🏠 Bosh menyu",
        "prev_button": "◀️",
        "next_button": "▶️",
        "select_language_button": "Tilni tanlash",
        "select_language_text": "Iltimos, tilni tanlang:",
        "start_message": "🏠 <b>Bosh menyu</b>",
        "help_button": "❓ Yordam",
        "back_button": "🔙 Orqaga",
        "help_start": "Assalomu alaykum, {full_name}! 👋\n\nSavolingizni shu yerga yozing. Adminlarimiz javob berishadi.",
        "help_forwarded": "✅ Sizning xabaringiz adminga yuborildi. Tez orada javob beramiz.",
        "help_cancelled": "Yordam so'rash bekor qilindi."
    },
    "ru": {
        "welcome": "Привет! Добро пожаловать в бот для поиска грузов. Пожалуйста, выберите язык:",
        "main_menu": "Используйте следующие кнопки:",
        "search_load": "🚛 Поиск груза",
        "add_group": "👥 Добавить группу",
        "add_contact": "📞 Добавить контакт",
        "check_balance": "💰 Проверить баланс",
        "send_feedback": "✍️ Оставить отзыв",

        "balance_check_title": "💰 <b>Проверка баланса</b>",
        "current_balance": "Ваш текущий баланс: {balance} сум",
        "contact_admin": "Для пополнения баланса свяжитесь с администратором: @Xx19_99",
        "language_selected": "Язык успешно установлен: Русский",
        "invalid_language": "Неверный выбор языка. Пожалуйста, нажмите одну из кнопок.",
        "admin_panel_close": "✅ Админ-панель закрыта",
        "admin_not_authorized": "❌ Вы не администратор!",
        "admin_panel_welcome": "👨‍💻 <b>Админ-панель</b>\n\nИспользуйте следующие функции:",
        "groups_button": "👥 Группы",
        "contacts_button": "📞 Контакты",
        "add_balance_button": "💰 Добавить баланс",
        "close_button": "❌ Закрыть",
        "feedback_list_button": "Список отзывов",
        "no_groups_found": "❌ Группы не найдены!",
        "all_groups_title": "👥 <b>Все группы</b>",
        "more_groups": "📝 ... и еще {count} групп",
        "no_contacts_found": "❌ Контакты не найдены!",
        "all_contacts_title": "📞 <b>Все контакты</b>",
        "more_contacts": "📝 ... и еще {count} контактов",
        "add_balance_title": "💰 <b>Добавление баланса</b>",
        "add_balance_format": "Введите ID пользователя и сумму:\n\nФормат: `user_id:сумма`\nПример: `123456789:50000`",
        "feedback_list_title": "<b>Список отзывов:</b>",
        "no_feedback_yet": "Отзывов пока нет.",
        "admin_unexpected_error": "❌ В админ-панели произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.",
        "add_balance_wrong_format": "❌ Неверный формат!\n\nПожалуйста, введите в следующем формате:\n`user_id:сумма`\n\nПример: `123456789:50000`",
        "balance_added_success": "✅ Баланс успешно добавлен!\n\n👤 ID пользователя: {user_id}\n💰 Сумма: {amount} сум",
        "contact_add_start": "📞 <b>Добавление контакта</b>\n\nОтправьте контактную информацию (имя пользователя или номер телефона):",
        "contact_add_success": "✅ Контакт успешно добавлен:\n`{contact_info}`",
        "contact_add_error": "❌ Произошла ошибка при добавлении контакта или контакт уже существует.",
        "contact_add_cancelled": "Добавление контакта отменено.",
        "feedback_start": "Напишите свой отзыв. Мы используем его для улучшения.",
        "feedback_thanks": "Спасибо за ваш отзыв!",
        "feedback_cancelled": "Отправка отзыва отменена.",
        "group_add_start": "👥 <b>Добавление группы</b>\n\nОтправьте ID группы, имя пользователя или ссылку:",
        "group_add_success": "✅ Группа успешно добавлена:\n`{group_id}`",
        "group_add_error": "❌ Произошла ошибка при добавлении группы или группа уже существует.",
        "group_add_cancelled": "Добавление группы отменено.",
        "search_error_telethon_not_connected": "❌ <b>Ошибка!</b>\n\nTelethon не подключен. Перезапустите бота.\nСвяжитесь с администратором: @Xx19_99",
        "search_from_city_prompt": "📍 <b>Откуда вы ищете груз?\n(Введите название города)</b>",
        "search_to_city_prompt": "📍 <b>Куда нужно?\n(Введите название города назначения)</b>",
        "search_in_progress": "🔍 <b>Процесс поиска</b>\n\n📍 {from_city} ➡️ {to_city}\n\n⏳ Поиск по группам...",
        "search_results_found": "✅ <b>Найдено {count} грузов!</b>\n\n🔍 {from_city} ➡️ {to_city}",
        "search_more_results": "📝 И еще {count} результатов...",
        "search_no_results": "❌ <b>Груз не найден</b>\n\n🔍 {from_city} ➡️ {to_city}\n\n<b>Ehtimoliy sabablar:</b>\n• Грузов по этому направлению нет\n• Группы закрыты или недоступны\n• Нет активности за последние дни\n\n💡 Попробуйте другие направления",
        "search_error_unexpected": "❌ В процессе поиска произошла ошибка. Пожалуйста, попробуйте позже.",
        "search_cancelled": "Поиск отменен.",
        "help_message": "Пожалуйста, напишите @Xx19_99 – мы немедленно вам поможем! 😊",
        "confirm_button": "Tasdiqlash",

        "search_result_item": "<b>#{i} {group_title}</b>\n\n📅 {date} | 👤 {sender}\n\n💬 {text}{ellipsis}\n\n🔗 <a href='{link}'>Xabarni ko'rish</a>",
        "search_result_item_list": "{idx}.) 🌍 {title} | 🇺🇿 | LOGISTICA 🌍\n💬 {text}",
        "search_list_header": "Страница {page} / {total}\n\n📍 {from_city} ➡️ {to_city}\n\nВсего найдено: {count} результатов",
        "search_details_header": "<b>#{idx} {title}</b>\n\n📅 {date} | 👤 {sender}\n\n",
        "back_to_list": "🔙 К списку",
        "main_menu_button": "🏠 Главное меню",
        "prev_button": "◀️",
        "next_button": "▶️",
        "select_language_button": "🇷🇺/🇺🇿 Сменить язык",
        "select_language_text": "Пожалуйста, выберите язык:",
        "start_message": "🚀 @logi_peek_bot — умный помощник для поиска грузов!\n\nЭтот бот поможет вам быстро, удобно и надежно выполнять логистические задачи:\n\n🔍 <b>Быстрый поиск грузов</b>\n— Найдите нужные грузы за несколько секунд\n\n👥 <b>Работа с контактами и группами</b>\n— Прямая связь с грузовладельцами и водителями\n\n💰 <b>Управление балансом</b>\n— Проверка и легкое пополнение баланса\n\n👉 Нажмите кнопку /start в боте, чтобы начать.",
        "help_button": "❓ Помощь",
        "back_button": "🔙 Назад",
        "help_start": "Здравствуйте, {full_name}! 👋\n\nНапишите ваш вопрос здесь. Наши администраторы ответят вам.",
        "help_forwarded": "✅ Ваше сообщение отправлено администратору. Мы ответим в ближайшее время.",
        "help_cancelled": "Запрос помощи отменен."
    },
    "en": {
        "welcome": "Hello! Welcome to the load search bot. Please select a language:",
        "main_menu": "Use the following buttons:",
        "search_load": "🚛 Search Load",
        "add_group": "👥 Add Group",
        "add_contact": "📞 Add Contact",
        "check_balance": "💰 Check Balance",
        "send_feedback": "✍️ Send Feedback",

        "balance_check_title": "💰 <b>Balance Check</b>",
        "current_balance": "Your current balance: {balance} UZS",
        "contact_admin": "Contact admin to top up balance: @Xx19_99",
        "language_selected": "Language successfully set: English",
        "invalid_language": "Invalid language selection. Please click one of the buttons.",
        "admin_panel_close": "✅ Admin panel closed",
        "admin_not_authorized": "❌ You are not an admin!",
        "admin_panel_welcome": "👨‍💻 <b>Admin Panel</b>\n\nUse the following functions:",
        "groups_button": "👥 Groups",
        "contacts_button": "📞 Contacts",
        "add_balance_button": "💰 Add Balance",
        "close_button": "❌ Close",
        "feedback_list_button": "Feedback List",
        "no_groups_found": "❌ No groups found!",
        "all_groups_title": "👥 <b>All Groups</b>",
        "more_groups": "📝 ... and {count} more groups",
        "no_contacts_found": "❌ No contacts found!",
        "all_contacts_title": "📞 <b>All Contacts</b>",
        "more_contacts": "📝 ... and {count} more contacts",
        "add_balance_title": "💰 <b>Add Balance</b>",
        "add_balance_format": "Enter User ID and amount:\n\nFormat: `user_id:amount`\nExample: `123456789:50000`",
        "feedback_list_title": "<b>Feedback List:</b>",
        "no_feedback_yet": "No feedback yet.",
        "admin_unexpected_error": "❌ Unexpected error in admin panel. Please try again later.",
        "add_balance_wrong_format": "❌ Invalid format!\n\nPlease enter in the following format:\n`user_id:amount`\n\nExample: `123456789:50000`",
        "balance_added_success": "✅ Balance successfully added!\n\n👤 User ID: {user_id}\n💰 Amount: {amount} UZS",
        "contact_add_start": "📞 <b>Add Contact</b>\n\nSend contact info (username or phone number):",
        "contact_add_success": "✅ Contact successfully added:\n`{contact_info}`",
        "contact_add_error": "❌ Error adding contact or contact already exists.",
        "contact_add_cancelled": "Add contact cancelled.",
        "feedback_start": "Write your feedback. We will use it to improve.",
        "feedback_thanks": "Thanks for your feedback!",
        "feedback_cancelled": "Feedback cancelled.",
        "group_add_start": "👥 <b>Add Group</b>\n\nSend group ID, username or link:",
        "group_add_success": "✅ Group successfully added:\n`{group_id}`",
        "group_add_error": "❌ Error adding group or group already exists.",
        "group_add_cancelled": "Add group cancelled.",
        "search_error_telethon_not_connected": "❌ <b>Error!</b>\n\nTelethon not connected. Restart the bot.\nContact admin: @Xx19_99",
        "search_from_city_prompt": "📍 <b>Where are you shipping from?\n(Enter city name)</b>",
        "search_to_city_prompt": "📍 <b>Where to?\n(Enter destination city)</b>",
        "search_in_progress": "🔍 <b>Search in progress</b>\n\n📍 {from_city} ➡️ {to_city}\n\n⏳ Searching in groups...",
        "search_results_found": "✅ <b>Found {count} loads!</b>\n\n🔍 {from_city} ➡️ {to_city}",
        "search_more_results": "📝 And {count} more results...",
        "search_no_results": "❌ <b>No loads found</b>\n\n🔍 {from_city} ➡️ {to_city}\n\n<b>Possible reasons:</b>\n• No loads on this route\n• Groups are closed or unavailable\n• No activity in recent days\n\n💡 Try other routes",
        "search_error_unexpected": "❌ Unexpected error during search. Please try again later.",
        "search_cancelled": "Search cancelled.",
        "help_message": "Please write to @Xx19_99 – we will help you immediately! 😊",
        "confirm_button": "Confirm",

        "search_result_item": "<b>#{i} {group_title}</b>\n\n📅 {date} | 👤 {sender}\n\n💬 {text}{ellipsis}\n\n🔗 <a href='{link}'>View Message</a>",
        "search_result_item_list": "{idx}.) 🌍 {title} | 🇺🇿 | LOGISTICA 🌍\n💬 {text}",
        "search_list_header": "Page {page} / {total}\n\n📍 {from_city} ➡️ {to_city}\n\nTotal found: {count} results",
        "search_details_header": "<b>#{idx} {title}</b>\n\n📅 {date} | 👤 {sender}\n\n",
        "back_to_list": "🔙 Back to List",
        "main_menu_button": "🏠 Main Menu",
        "prev_button": "◀️",
        "next_button": "▶️",
        "select_language_button": "Change Language",
        "select_language_text": "Please select language:",
        "start_message": "🚀 @logi_peek_bot — smart assistant for finding loads!\n\nThis bot helps you perform logistics tasks quickly, conveniently and reliably:\n\n🔍 <b>Fast Load Search</b>\n— Find loads in seconds\n\n👥 <b>Work with Contacts and Groups</b>\n— Direct communication with load owners and drivers\n\n💰 <b>Balance Management</b>\n— Check and easily top up balance\n\n👉 Click /start button in the bot to begin.",
        "help_button": "❓ Help",
        "back_button": "🔙 Back",
        "help_start": "Hello, {full_name}! 👋\n\nWrite your question here. Our admins will answer you.",
        "help_forwarded": "✅ Your message has been sent to the admin. We will answer soon.",
        "help_cancelled": "Help request cancelled."
    }
}

def get_message(user_data, key, **kwargs):
    lang = user_data.get('language', 'uz') # Default til 'uz'
    message = MESSAGES.get(lang, {}).get(key, MESSAGES['uz'][key]) # Agar tanlangan tilda bo'lmasa, 'uz' tilidan oladi
    return message.format(**kwargs)

async def start_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [KeyboardButton("🇺🇿 O'zbekcha"), KeyboardButton("🇷🇺 Русский")],
        [KeyboardButton("🇺🇸 English"), KeyboardButton(get_message(context.user_data, "back_button"))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        get_message(context.user_data, "select_language_text"), 
        reply_markup=reply_markup
    )
    return LanguageStates.SELECT_LANGUAGE


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip()
    user_id = update.effective_user.id
    
    logger.info(f"Language selection received: '{choice}' from User {user_id}")

    if choice == get_message(context.user_data, "back_button"):
        # Asosiy menyuga qaytish
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await update.message.reply_text(get_message(context.user_data, "main_menu"), reply_markup=reply_markup)
        return ConversationHandler.END

    # Agar foydalanuvchi "Tilni tanlash" tugmasini qayta bossa (yoki eski tugmani ishlatsa)
    if choice in [MESSAGES['uz']['select_language_button'], MESSAGES['ru']['select_language_button'], MESSAGES['en']['select_language_button']]:
        # Qayta til tanlash menyusini chiqarish
        keyboard = [
            [KeyboardButton("🇺🇿 O'zbekcha"), KeyboardButton("🇷🇺 Русский")],
            [KeyboardButton("🇺🇸 English"), KeyboardButton(get_message(context.user_data, "back_button"))]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            get_message(context.user_data, "select_language_text"), 
            reply_markup=reply_markup
        )
        return LanguageStates.SELECT_LANGUAGE

    if "O'zbekcha" in choice:
        context.user_data['language'] = 'uz'
        lang_code = 'uz'
    elif "Русский" in choice:
        context.user_data['language'] = 'ru'
        lang_code = 'ru'
    elif "English" in choice:
        context.user_data['language'] = 'en'
        lang_code = 'en'
    else:
        await update.message.reply_text(get_message(context.user_data, "invalid_language"))
        return LanguageStates.SELECT_LANGUAGE
    
    await update.message.reply_text(get_message(context.user_data, "language_selected"))
    logger.info(f"User {user_id} selected language: {lang_code}")
    
    # Til tanlangandan so'ng asosiy menyuni ko'rsatamiz
    reply_markup = get_main_menu_keyboard(context.user_data, get_message)
    await update.message.reply_text(get_message(context.user_data, "main_menu"), reply_markup=reply_markup)
    
    return ConversationHandler.END

def get_language_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("language", start_language_selection),
            MessageHandler(filters.Regex(f"^({MESSAGES['uz']['select_language_button']}|{MESSAGES['ru']['select_language_button']}|{MESSAGES['en']['select_language_button']})$"), start_language_selection)
        ],
        states={
            LanguageStates.SELECT_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)]
        },
        fallbacks=[] # Til tanlashda fallbacks hozircha kerak emas
    )
