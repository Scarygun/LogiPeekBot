import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from database import _read_json, _write_json
from config import USERS_JSON_FILE
import aiohttp
from language_handler import get_message
from keyboards import get_back_keyboard, get_main_menu_keyboard, get_auth_keyboard

logger = logging.getLogger(__name__)

WAITING_PHONE = 1
WAITING_PASSWORD = 2

async def start_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        "📱 <b>Tizimga kirish</b>\n\nVigo.uz tizimidagi telefon raqamingizni kiriting (masalan: +998901234567):",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return WAITING_PHONE

async def process_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    from language_handler import is_back_button
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    context.user_data['login_phone'] = text
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        "🔒 Endi Vigo.uz parolingizni kiriting:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return WAITING_PASSWORD

async def process_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    from language_handler import is_back_button
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    phone = context.user_data.get('login_phone')
    password = text
    
    # Try logging in to Vigo.uz
    loading_msg = await update.message.reply_text("⏳ Tizimga ulanmoqda...")
    
    try:
        import os
        base_url = os.getenv('BACKEND_API_URL', 'https://api.vigo.uz')
        login_url = f"{base_url}/api/v1/auth/login/"
        payload = {"phone": phone, "password": password}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(login_url, json=payload) as response:
                if response.status == 200:
                    # Success
                    user_id = str(update.effective_user.id)
                    users = _read_json(USERS_JSON_FILE, [])
                    
                    if isinstance(users, list):
                        for u in users:
                            if str(u.get("user_id")) == user_id:
                                u["vigo_phone"] = phone
                                u["vigo_password"] = password
                                break
                        else:
                            users.append({"user_id": int(user_id), "vigo_phone": phone, "vigo_password": password})
                    elif isinstance(users, dict):
                        if user_id not in users:
                            users[user_id] = {"user_id": int(user_id)}
                        users[user_id]["vigo_phone"] = phone
                        users[user_id]["vigo_password"] = password
                        
                    _write_json(USERS_JSON_FILE, users)
                    
                    reply_markup = get_main_menu_keyboard(context.user_data, get_message)
                    await context.bot.edit_message_text(
                        "✅ <b>Tizimga muvaffaqiyatli kirdingiz!</b>\n\nEndi bot xizmatlaridan foydalanishingiz mumkin.",
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id,
                        parse_mode="HTML"
                    )
                    await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
                else:
                    inline_kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔐 Parolni unutdingizmi?", callback_data="start_forgot_pw")]
                    ])
                    await context.bot.edit_message_text(
                        "❌ <b>Xatolik!</b>\nTelefon raqam yoki parol noto'g'ri.\nQaytadan parolni kiriting yoki parolni tiklang.",
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id,
                        parse_mode="HTML",
                        reply_markup=inline_kb
                    )
                    return WAITING_PASSWORD
    except Exception as e:
        logger.error(f"Login xatosi: {e}")
        await context.bot.edit_message_text(
            "❌ Server bilan bog'lanishda xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.",
            chat_id=update.effective_chat.id,
            message_id=loading_msg.message_id
        )
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

def get_login_conversation_handler():
    from language_handler import MESSAGES
    entry_buttons = [MESSAGES[lang]["login_button"] for lang in MESSAGES]
    
    return ConversationHandler(
        entry_points=[
            CommandHandler("login", start_login), 
            MessageHandler(filters.Text(entry_buttons), start_login)
        ],
        states={
            WAITING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_phone)],
            WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_password)],
        },
        fallbacks=[]
    )
