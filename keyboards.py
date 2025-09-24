from telegram import ReplyKeyboardMarkup, KeyboardButton
# from language_handler import get_message # Aylana import sababli o'chirildi

def get_main_menu_keyboard(user_data, get_message_func):
    keyboard = [
        [get_message_func(user_data, "search_load")],
        [get_message_func(user_data, "add_group"), get_message_func(user_data, "add_contact")],
        [get_message_func(user_data, "check_balance")], [get_message_func(user_data, "send_feedback")],
        [get_message_func(user_data, "select_language_button")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
