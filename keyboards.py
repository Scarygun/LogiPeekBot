from telegram import ReplyKeyboardMarkup
# from language_handler import get_message # Aylana import sababli o'chirildi

def get_main_menu_keyboard(user_data, get_message_func):
    keyboard = [
        [get_message_func(user_data, "search_load"), get_message_func(user_data, "help_button")],
        [get_message_func(user_data, "add_group"), get_message_func(user_data, "add_contact")],
        [get_message_func(user_data, "check_balance"), get_message_func(user_data, "send_feedback")],
        [get_message_func(user_data, "select_language_button")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_all_menu_buttons(get_message_func):
    """Barcha tillardagi asosiy menyu tugmalari ro'yxatini qaytaradi"""
    from language_handler import MESSAGES
    buttons = []
    keys = ["search_load", "add_group", "add_contact", "check_balance", "send_feedback",
            "select_language_button", "help_button", "sms_button"]
    for lang in MESSAGES:
        for key in keys:
            if key in MESSAGES[lang]:
                buttons.append(MESSAGES[lang][key])
    return list(set(buttons))

def get_back_keyboard(user_data, get_message_func):
    """Faqat 'Orqaga' tugmasi bor klaviatura"""
    keyboard = [
        [get_message_func(user_data, "back_button")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
