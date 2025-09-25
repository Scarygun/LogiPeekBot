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
        "broadcast_message_button": "📢 Xabar tarqatish",
        "balance_check_title": "💰 **Balans tekshirish**",
        "current_balance": "Hozirda sizning balansingiz: {balance} so'm",
        "contact_admin": "Balansingizni to'ldirish uchun admin bilan bog'laning: @Xx19_99",
        "language_selected": "Til muvaffaqiyatli o'rnatildi: O'zbekcha",
        "invalid_language": "Noto'g'ri til tanlovi. Iltimos, tugmalardan birini bosing.",
        "admin_panel_close": "✅ Admin panel yopildi",
        "admin_not_authorized": "❌ Siz admin emassiz!",
        "admin_panel_welcome": "👨‍💻 **Admin Panel**\n\nQuyidagi funksiyalardan foydalaning:",
        "stats_button": "📊 Statistika",
        "groups_button": "👥 Guruhlar",
        "contacts_button": "📞 Kontaktlar",
        "add_balance_button": "💰 Balans qo'shish",
        "close_button": "❌ Yopish",
        "feedback_list_button": "Fikrlar ro'yxati",
        "bot_stats_title": "📊 **Bot Statistikasi**",
        "group_count": "👥 Guruhlar soni: {count}",
        "contact_count": "📞 Kontaktlar soni: {count}",
        "last_update": "🔄 Oxirgi yangilanish: Hozir",
        "no_groups_found": "❌ Guruhlar topilmadi!",
        "all_groups_title": "👥 **Barcha Guruhlar**",
        "more_groups": "📝 ... va yana {count} ta guruh",
        "no_contacts_found": "❌ Kontaktlar topilmadi!",
        "all_contacts_title": "📞 **Barcha Kontaktlar**",
        "more_contacts": "📝 ... va yana {count} ta kontakt",
        "add_balance_title": "💰 **Balans Qo'shish**",
        "add_balance_format": "Foydalanuvchi ID sini va miqdorni kiriting:\n\nFormat: `user_id:miqdor`\nMisol: `123456789:50000`",
        "feedback_list_title": "**Fikrlar ro'yxati:**",
        "no_feedback_yet": "Hali hech qanday fikr bildirilmagan.",
        "admin_unexpected_error": "❌ Admin panelda kutilmagan xato yuz berdi. Iltimos, keyinroq urinib ko'ring.",
        "add_balance_wrong_format": "❌ Noto'g'ri format!\n\nIltimos, quyidagi formatda kiriting:\n`user_id:miqdor`\n\nMisol: `123456789:50000`",
        "balance_added_success": "✅ Balans muvaffaqiyatli qo'shildi!\n\n👤 Foydalanuvchi ID: {user_id}\n💰 Miqdor: {amount} so'm",
        "contact_add_start": "📞 **Kontakt qo'shish**\n\nKontakt ma'lumotlarini yuboring (username yoki telefon raqam):",
        "contact_add_success": "✅ Kontakt muvaffaqiyatli qo'shildi:\n`{contact_info}`",
        "contact_add_error": "❌ Kontaktni qo'shishda xatolik yuz berdi yoki kontakt allaqachon mavjud.",
        "contact_add_cancelled": "Kontakt qo'shish bekor qilindi.",
        "feedback_start": "Fikringizni yozing. Biz uni yaxshilash uchun foydalanamiz.",
        "feedback_thanks": "Fikringiz uchun rahmat!",
        "feedback_cancelled": "Fikr bildirish bekor qilindi.",
        "group_add_start": "👥 **Guruh qo'shish**\n\nGuruh ID, username yoki linkini yuboring:",
        "group_add_success": "✅ Guruh muvaffaqiyatli qo'shildi:\n`{group_id}`",
        "group_add_error": "❌ Guruhni qo'shishda xatolik yuz berdi yoki guruh allaqachon mavjud.",
        "group_add_cancelled": "Guruh qo'shish bekor qilindi.",
        "search_error_telethon_not_connected": "❌ **Xato!**\n\nTelethon ulanmagan. Botni qayta ishga tushiring.\nAdmin bilan bog'laning: @Xx19_99",
        "search_from_city_prompt": "📍 **Qayerdan yuk qidiryapsiz?\n(Shahar nomini kiriting)**",
        "search_to_city_prompt": "📍 **Qayergacha kerak?\n(Maqsad shahrini kiriting)**",
        "search_in_progress": "🔍 **Qidiruv jarayoni**\n\n📍 {from_city} ➡️ {to_city}\n\n⏳ Guruhlardan qidirilmoqda...",
        "search_results_found": "✅ **{count} ta yuk topildi!**\n\n🔍 {from_city} ➡️ {to_city}",
        "search_more_results": "📝 Va yana {count} ta natija bor...",
        "search_no_results": "❌ **Yuk topilmadi**\n\n🔍 {from_city} ➡️ {to_city}\n\n**Ehtimoliy sabablar:**\n• Bu yo'nalishda yuk yo'q\n• Guruhlar yopiq yoki mavjud emas\n• So'nggi kunlarda faollik yo'q\n\n💡 Boshqa yo'nalishlarni sinab ko'ring",
        "search_error_unexpected": "❌ Qidiruv jarayonida xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
        "search_cancelled": "Qidiruv bekor qilindi.",
        "help_message": "Iltimos, @Xx19_99 ga yozing – biz sizga zudlik bilan yordam beramiz! 😊",
        "cancel_button": "Bekor qilish",
        "confirm_button": "Tasdiqlash",
        "broadcast_start_message": "Tarqatmoqchi bo'lgan xabaringizni kiriting:",
        "broadcast_confirm_message": "Quyidagi xabarni tarqatishni tasdiqlaysizmi?\n\n{message}",
        "invalid_choice": "Noto'g'ri tanlov. Iltimos, tugmalardan birini bosing.",
        "broadcast_cancelled": "Xabar tarqatish bekor qilindi.",
        "broadcast_error": "❌ Xabar yuborishda xato. Iltimos, keyinroq urinib ko'ring.",
        "broadcast_success": "✅ Xabar muvaffaqiyatli tarqatildi!\n\nSent: {sent}\nFailed: {failed}",
        "search_result_item": "**#{i} {group_title}**\n\n📅 {date} | 👤 {sender}\n\n💬 {text}{ellipsis}\n\n🔗 [Xabarni ko'rish]({link})",
        "select_language_button": "Tilni tanlash",
        "select_language_text": "Iltimos, tilni tanlang:",
        "bot_description_title": "Bot nima qila oladi?",
        "bot_description_line1": "🚀 Bu bot sizga yuk topishda yordam beradi!",
        "bot_username": "@logi_peek_bot", # Example bot username, replace if actual is different
        "bot_description_line2_8d": "🔍 Tez va oson yuk qidirish",
        "bot_description_line3_concert": "👥 Guruhlar va kontaktlar qo'shish",
        "bot_description_line4_slowed": "💰 Balansingizni tekshirish va to'ldirish",
        "bot_description_line5_all_in_seconds": "👉 Barcha funksiyalar bir joyda"
    },
    "ru": {
        "welcome": "Привет! Добро пожаловать в бот для поиска грузов. Пожалуйста, выберите язык:",
        "main_menu": "Используйте следующие кнопки:",
        "search_load": "🚛 Поиск груза",
        "add_group": "👥 Добавить группу",
        "add_contact": "📞 Добавить контакт",
        "check_balance": "💰 Проверить баланс",
        "send_feedback": "✍️ Оставить отзыв",
        "broadcast_message_button": "📢 Рассылка сообщений",
        "balance_check_title": "💰 **Проверка баланса**",
        "current_balance": "Ваш текущий баланс: {balance} сум",
        "contact_admin": "Для пополнения баланса свяжитесь с администратором: @Xx19_99",
        "language_selected": "Язык успешно установлен: Русский",
        "invalid_language": "Неверный выбор языка. Пожалуйста, нажмите одну из кнопок.",
        "admin_panel_close": "✅ Админ-панель закрыта",
        "admin_not_authorized": "❌ Вы не администратор!",
        "admin_panel_welcome": "👨‍💻 **Админ-панель**\n\nИспользуйте следующие функции:",
        "stats_button": "📊 Статистика",
        "groups_button": "👥 Группы",
        "contacts_button": "📞 Контакты",
        "add_balance_button": "💰 Добавить баланс",
        "close_button": "❌ Закрыть",
        "feedback_list_button": "Список отзывов",
        "bot_stats_title": "📊 **Статистика бота**",
        "group_count": "👥 Количество групп: {count}",
        "contact_count": "📞 Количество контактов: {count}",
        "last_update": "🔄 Последнее обновление: Сейчас",
        "no_groups_found": "❌ Группы не найдены!",
        "all_groups_title": "👥 **Все группы**",
        "more_groups": "📝 ... и еще {count} групп",
        "no_contacts_found": "❌ Контакты не найдены!",
        "all_contacts_title": "📞 **Все контакты**",
        "more_contacts": "📝 ... и еще {count} контактов",
        "add_balance_title": "💰 **Добавление баланса**",
        "add_balance_format": "Введите ID пользователя и сумму:\n\nФормат: `user_id:сумма`\nПример: `123456789:50000`",
        "feedback_list_title": "**Список отзывов:**",
        "no_feedback_yet": "Отзывов пока нет.",
        "admin_unexpected_error": "❌ В админ-панели произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.",
        "add_balance_wrong_format": "❌ Неверный формат!\n\nПожалуйста, введите в следующем формате:\n`user_id:сумма`\n\nПример: `123456789:50000`",
        "balance_added_success": "✅ Баланс успешно добавлен!\n\n👤 ID пользователя: {user_id}\n💰 Сумма: {amount} сум",
        "contact_add_start": "📞 **Добавление контакта**\n\nОтправьте контактную информацию (имя пользователя или номер телефона):",
        "contact_add_success": "✅ Контакт успешно добавлен:\n`{contact_info}`",
        "contact_add_error": "❌ Произошла ошибка при добавлении контакта или контакт уже существует.",
        "contact_add_cancelled": "Добавление контакта отменено.",
        "feedback_start": "Напишите свой отзыв. Мы используем его для улучшения.",
        "feedback_thanks": "Спасибо за ваш отзыв!",
        "feedback_cancelled": "Отправка отзыва отменена.",
        "group_add_start": "👥 **Добавление группы**\n\nОтправьте ID группы, имя пользователя или ссылку:",
        "group_add_success": "✅ Группа успешно добавлена:\n`{group_id}`",
        "group_add_error": "❌ Произошла ошибка при добавлении группы или группа уже существует.",
        "group_add_cancelled": "Добавление группы отменено.",
        "search_error_telethon_not_connected": "❌ **Ошибка!**\n\nTelethon не подключен. Перезапустите бота.\nСвяжитесь с администратором: @Xx19_99",
        "search_from_city_prompt": "📍 **Откуда вы ищете груз?\n(Введите название города)**",
        "search_to_city_prompt": "📍 **Куда нужно?\n(Введите название города назначения)**",
        "search_in_progress": "🔍 **Процесс поиска**\n\n📍 {from_city} ➡️ {to_city}\n\n⏳ Поиск по группам...",
        "search_results_found": "✅ **Найдено {count} грузов!**\n\n🔍 {from_city} ➡️ {to_city}",
        "search_more_results": "📝 И еще {count} результатов...",
        "search_no_results": "❌ **Груз не найден**\n\n🔍 {from_city} ➡️ {to_city}\n\n**Возможные причины:**\n• Грузов по этому направлению нет\n• Группы закрыты или недоступны\n• Нет активности за последние дни\n\n💡 Попробуйте другие направления",
        "search_error_unexpected": "❌ В процессе поиска произошла ошибка. Пожалуйста, попробуйте позже.",
        "search_cancelled": "Поиск отменен.",
        "help_message": "Пожалуйста, напишите @Xx19_99 – мы немедленно вам поможем! 😊",
        "cancel_button": "Bekor qilish",
        "confirm_button": "Tasdiqlash",
        "broadcast_start_message": "Tarqatmoqchi bo'lgan xabaringizni kiriting:",
        "broadcast_confirm_message": "Quyidagi xabarni tarqatishni tasdiqlaysizmi?\n\n{message}",
        "invalid_choice": "Noto'g'ri tanlov. Iltimos, tugmalardan birini bosing.",
        "broadcast_cancelled": "Xabar tarqatish bekor qilindi.",
        "broadcast_error": "❌ Xabar yuborishda xato. Iltimos, keyinroq urinib ko'ring.",
        "broadcast_success": "✅ Xabar muvaffaqiyatli tarqatildi!\n\nSent: {sent}\nFailed: {failed}",
        "search_result_item": "**#{i} {group_title}**\n\n📅 {date} | 👤 {sender}\n\n💬 {text}{ellipsis}\n\n🔗 [Xabarni ko'rish]({link})",
        "select_language_button": "Tilni tanlash",
        "select_language_text": "Iltimos, tilni tanlang:",
        "bot_description_title": "Bot nima qila oladi?",
        "bot_description_line1": "🚀 Bu bot sizga yuk topishda yordam beradi!",
        "bot_username": "@YukQidirishBot", # Example bot username, replace if actual is different
        "bot_description_line2_8d": "🔍 Tez va oson yuk qidirish",
        "bot_description_line3_concert": "👥 Guruhlar va kontaktlar qo'shish",
        "bot_description_line4_slowed": "💰 Balansingizni tekshirish va to'ldirish",
        "bot_description_line5_all_in_seconds": "👉 Barcha funksiyalar bir joyda"
    }
}

def get_message(user_data, key, **kwargs):
    lang = user_data.get('language', 'uz') # Default til 'uz'
    message = MESSAGES.get(lang, {}).get(key, MESSAGES['uz'][key]) # Agar tanlangan tilda bo'lmasa, 'uz' tilidan oladi
    return message.format(**kwargs)

async def start_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [KeyboardButton("🇺🇿 O'zbekcha")],
        [KeyboardButton("🇷🇺 Русский")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        get_message(context.user_data, "select_language_text"), 
        reply_markup=reply_markup
    )
    return LanguageStates.SELECT_LANGUAGE


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    user_id = update.effective_user.id
    
    if "O'zbekcha" in choice:
        context.user_data['language'] = 'uz'
        lang_code = 'uz'
    elif "Русский" in choice:
        context.user_data['language'] = 'ru'
        lang_code = 'ru'
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
            MessageHandler(filters.Regex(f"^({MESSAGES['uz']['select_language_button']}|{MESSAGES['ru']['select_language_button']})$"), start_language_selection)
        ],
        states={
            LanguageStates.SELECT_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)]
        },
        fallbacks=[] # Til tanlashda fallbacks hozircha kerak emas
    )
