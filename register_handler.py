import logging
import os
import aiohttp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from database import _read_json, _write_json
from config import USERS_JSON_FILE
from language_handler import get_message, is_back_button
from keyboards import get_back_keyboard, get_main_menu_keyboard, get_auth_keyboard

logger = logging.getLogger(__name__)

WAITING_REG_PHONE = 1
WAITING_REG_OTP = 2
WAITING_REG_FULL_NAME = 4
WAITING_REG_PASSWORD = 5

async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        "📝 <b>Ro'yxatdan o'tish</b>\n\nIltimos, telefon raqamingizni kiriting (masalan: +998901234567):",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return WAITING_REG_PHONE

async def process_reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    phone = text
    context.user_data['reg_phone'] = phone
    loading_msg = await update.message.reply_text("⏳ Raqam tekshirilmoqda...")

    try:
        base_url = os.getenv('BACKEND_API_URL', 'https://api.vigo.uz')
        start_url = f"{base_url}/api/v1/auth/register/start/"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(start_url, json={"phone": phone}) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    deep_link = data.get("telegram_deep_link")
                    
                    if deep_link:
                        reply_markup = InlineKeyboardMarkup([
                            [InlineKeyboardButton("📱 Kodni olish", url=deep_link)]
                        ])
                        await context.bot.edit_message_text(
                            "📲 Xavfsizlik kodi yuborildi!\n\n"
                            "Iltimos, pastdagi tugmani bosib, OTP botga o'ting va raqamingizni tasdiqlang. "
                            "So'ngra, u yerdan kelgan <b>tasdiqlash kodini</b> shu yerga yozing:",
                            chat_id=update.effective_chat.id,
                            message_id=loading_msg.message_id,
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                    else:
                        await context.bot.edit_message_text(
                            "📲 Tasdiqlash kodi telefoningizga yuborildi. Iltimos kodni kiriting:",
                            chat_id=update.effective_chat.id,
                            message_id=loading_msg.message_id
                        )
                    
                    # Orqaga tugmasi turishi uchun
                    await update.message.reply_text("Kutmoqdaman...", reply_markup=get_back_keyboard(context.user_data, get_message))
                    return WAITING_REG_OTP
                else:
                    error_text = await response.text()
                    logger.error(f"OTP so'rash xatosi: {response.status} - {error_text}")
                    reply_markup = get_auth_keyboard(context.user_data, get_message)
                    await context.bot.edit_message_text(
                        "❌ Xatolik! Bunday raqam band bo'lishi mumkin yoki noto'g'ri format.\nIltimos, tekshirib qaytadan urinib ko'ring.",
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id
                    )
                    await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
                    return ConversationHandler.END
    except Exception as e:
        logger.error(f"API Error: {e}")
        await context.bot.edit_message_text("❌ Server bilan aloqa yo'q.", chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
        return ConversationHandler.END

async def process_reg_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    otp_code = text
    phone = context.user_data.get('reg_phone')
    loading_msg = await update.message.reply_text("⏳ Kod tekshirilmoqda...")

    try:
        base_url = os.getenv('BACKEND_API_URL', 'https://api.vigo.uz')
        verify_url = f"{base_url}/api/v1/auth/register/verify/"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(verify_url, json={"phone": phone, "otp": otp_code}) as response:
                if response.status in [200, 201]:
                    try:
                        data = await response.json()
                        context.user_data['reg_token'] = data.get('registration_token', '12345678901234567890123456789012')
                    except Exception:
                        context.user_data['reg_token'] = '12345678901234567890123456789012'

                    context.user_data['reg_role'] = 'driver'
                    reply_markup = get_back_keyboard(context.user_data, get_message)
                    await context.bot.edit_message_text(
                        "✅ Kod tasdiqlandi!\n\nEndi to'liq ismingizni (F.I.O) kiriting:",
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id
                    )
                    return WAITING_REG_FULL_NAME
                else:
                    await context.bot.edit_message_text(
                        "❌ Kod noto'g'ri! Iltimos, tekshirib qaytadan yozing:",
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id
                    )
                    return WAITING_REG_OTP
    except Exception as e:
        logger.error(f"API Error: {e}")
        await context.bot.edit_message_text("❌ Server bilan aloqa yo'q.", chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
        return ConversationHandler.END

# process_reg_role_callback va process_reg_role_text o'chirildi

async def process_reg_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    context.user_data['reg_full_name'] = text
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text("O'zingiz uchun kuchli parol o'ylab toping:", reply_markup=reply_markup)
    return WAITING_REG_PASSWORD

async def process_reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    password = text
    
    import re
    if not (re.search(r'[A-Z]', password) and re.search(r'\d', password) and re.search(r'[^a-zA-Z0-9\s]', password)):
        await update.message.reply_text(
            "❌ <b>Parol juda oddiy!</b>\n\n"
            "Xavfsizlik uchun parolda quyidagilar bo'lishi shart:\n"
            "• Kamida bitta <b>bosh harf</b> (A-Z)\n"
            "• Kamida bitta <b>raqam</b> (0-9)\n"
            "• Kamida bitta <b>maxsus belgi</b> (!, @, #, $, % va hokazo)\n\n"
            "Misol uchun: <code>Vigo2026!@</code>\n\n"
            "Iltimos, qaytadan kuchliroq parol kiriting:",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(context.user_data, get_message)
        )
        return WAITING_REG_PASSWORD
    phone = context.user_data.get('reg_phone')
    role = context.user_data.get('reg_role')
    full_name = context.user_data.get('reg_full_name')
    reg_token = context.user_data.get('reg_token', '12345678901234567890123456789012')

    loading_msg = await update.message.reply_text("⏳ Akkaunt yaratilmoqda...")

    try:
        base_url = os.getenv('BACKEND_API_URL', 'https://api.vigo.uz')
        register_url = f"{base_url}/api/v1/auth/register/"
        
        payload = {
            "phone": phone,
            "full_name": full_name,
            "password": password,
            "confirm_password": password,
            "role": role,
            "registration_token": reg_token
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(register_url, json=payload) as response:
                if response.status in [200, 201]:
                    # Muvaffaqiyatli saqlandi
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
                        "🎉 <b>Tabriklaymiz! Muvaffaqiyatli ro'yxatdan o'tdingiz.</b>",
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id,
                        parse_mode="HTML"
                    )
                    await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
                else:
                    error_text = await response.text()
                    logger.error(f"Ro'yxatdan o'tish yakunida xato: {response.status} - {error_text}")
                    reply_markup = get_auth_keyboard(context.user_data, get_message)
                    await context.bot.edit_message_text(
                        f"❌ Xatolik yuz berdi: Hamma ma'lumotlar to'g'riligini tekshiring.\n({response.status})",
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id
                    )
                    await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"API Error: {e}")
        await context.bot.edit_message_text("❌ Server xatosi.", chat_id=update.effective_chat.id, message_id=loading_msg.message_id)

    return ConversationHandler.END

def get_register_conversation_handler():
    from language_handler import MESSAGES
    register_buttons = [MESSAGES[lang]["register_button"] for lang in MESSAGES]
    
    return ConversationHandler(
        entry_points=[
            CommandHandler("register", start_register), 
            MessageHandler(filters.Text(register_buttons), start_register)
        ],
        states={
            WAITING_REG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_reg_phone)],
            WAITING_REG_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_reg_otp)],
            WAITING_REG_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_reg_full_name)],
            WAITING_REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_reg_password)],
        },
        fallbacks=[]
    )
