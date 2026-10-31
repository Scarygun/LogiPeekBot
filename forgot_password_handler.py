import logging
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from database import _read_json, _write_json
from config import USERS_JSON_FILE
from language_handler import get_message, is_back_button
from keyboards import get_back_keyboard, get_main_menu_keyboard, get_auth_keyboard
from backend_client import backend_client

logger = logging.getLogger(__name__)

WAITING_FORGOT_PHONE = 1
WAITING_FORGOT_OTP = 2
WAITING_FORGOT_PASSWORD = 3
WAITING_FORGOT_CONFIRM = 4

async def start_forgot_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_back_keyboard(context.user_data, get_message)
    
    # Agar foydalanuvchi avval login paytida raqam kiritgan bo'lsa
    existing_phone = context.user_data.get('login_phone')
    hint = f"\n(Masalan: <code>{existing_phone}</code>)" if existing_phone else ""
    
    text = (
        "🔐 <b>Parolni tiklash</b>\n\n"
        "Vigo.uz tizimidagi ro'yxatdan o'tgan telefon raqamingizni kiriting:\n"
        "<i>Format: +998901234567</i>" + hint
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    return WAITING_FORGOT_PHONE

async def process_forgot_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    # Raqamni tozalash va tekshirish
    phone = text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        if phone.startswith('998'):
            phone = '+' + phone
        elif len(phone) == 9:
            phone = '+998' + phone

    if not re.match(r'^\+998\d{9}$', phone):
        await update.message.reply_text(
            "❌ <b>Noto'g'ri telefon raqami formati!</b>\n"
            "Iltimos, raqamni to'liq kiriting (masalan: +998901234567):",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(context.user_data, get_message)
        )
        return WAITING_FORGOT_PHONE

    context.user_data['forgot_phone'] = phone
    loading_msg = await update.message.reply_text("⏳ Tekshirilmoqda va tasdiqlash kodi so'ralmoqda...")

    success, data = await backend_client.forgot_password(phone)
    if success and isinstance(data, dict):
        deep_link = data.get("telegram_deep_link")
        if deep_link:
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Kodni olish (OTP Bot)", url=deep_link)]
            ])
            await context.bot.edit_message_text(
                "📲 <b>Tasdiqlash kodi yuborildi!</b>\n\n"
                "Iltimos, pastdagi tugmani bosib, OTP botga kiring va tasdiqlash kodini oling.\n\n"
                "So'ngra olingan <b>kodni (OTP)</b> shu yerga yozib yuboring:",
                chat_id=update.effective_chat.id,
                message_id=loading_msg.message_id,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await context.bot.edit_message_text(
                "📲 <b>Tasdiqlash kodi telefoningizga yuborildi.</b>\n\nIltimos, kodni kiriting:",
                chat_id=update.effective_chat.id,
                message_id=loading_msg.message_id,
                parse_mode="HTML"
            )
        
        await update.message.reply_text("Kutmoqdaman...", reply_markup=get_back_keyboard(context.user_data, get_message))
        return WAITING_FORGOT_OTP
    else:
        err_msg = str(data)
        logger.error(f"forgot_password error: {err_msg}")
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await context.bot.edit_message_text(
            "❌ <b>Xatolik yuz berdi!</b>\nBunday raqam topilmadi yoki tizimda vaqtinchalik nosozlik.\nIltimos, qaytadan urinib ko'ring.",
            chat_id=update.effective_chat.id,
            message_id=loading_msg.message_id,
            parse_mode="HTML"
        )
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

async def process_forgot_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    otp_code = text.replace(' ', '')
    if not otp_code.isalnum() or len(otp_code) < 4:
        await update.message.reply_text(
            "❌ Iltimos, tasdiqlash kodini to'g'ri kiriting:",
            reply_markup=get_back_keyboard(context.user_data, get_message)
        )
        return WAITING_FORGOT_OTP

    context.user_data['forgot_otp'] = otp_code
    reply_markup = get_back_keyboard(context.user_data, get_message)
    
    await update.message.reply_text(
        "✅ <b>Kodni qabul qildik!</b>\n\n"
        "Endi o'zingiz uchun <b>yangi parol</b> kiriting:\n\n"
        "<i>Talablar:</i>\n"
        "• Kamida 8 ta belgi\n"
        "• Kamida bitta bosh harf (A-Z)\n"
        "• Kamida bitta raqam (0-9)\n"
        "• Kamida bitta maxsus belgi (!@#$%...)",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return WAITING_FORGOT_PASSWORD

async def process_forgot_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    password = text
    if len(password) < 8:
        await update.message.reply_text(
            "❌ <b>Parol kamida 8 ta belgidan iborat bo'lishi kerak!</b>\nIltimos, boshqatdan kiriting:",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(context.user_data, get_message)
        )
        return WAITING_FORGOT_PASSWORD

    if not (re.search(r'[A-Z]', password) and re.search(r'\d', password) and re.search(r'[^a-zA-Z0-9\s]', password)):
        await update.message.reply_text(
            "❌ <b>Parol xavfsizlik talablariga javob bermaydi!</b>\n\n"
            "Parolda quyidagilar bo'lishi shart:\n"
            "• Kamida bitta <b>bosh harf</b> (A-Z)\n"
            "• Kamida bitta <b>raqam</b> (0-9)\n"
            "• Kamida bitta <b>maxsus belgi</b> (!@#$%^&*)\n\n"
            "Iltimos, qaytadan kiriting:",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(context.user_data, get_message)
        )
        return WAITING_FORGOT_PASSWORD

    context.user_data['forgot_new_password'] = password
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        "🔒 <b>Yangi parolni tasdiqlash uchun qaytadan kiriting:</b>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return WAITING_FORGOT_CONFIRM

async def process_forgot_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_back_button(text):
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END

    confirm_password = text
    new_password = context.user_data.get('forgot_new_password')
    
    if confirm_password != new_password:
        await update.message.reply_text(
            "❌ <b>Kiritilgan parollar bir-biriga mos kelmadi!</b>\n\n"
            "Iltimos, tasdiqlash parolini qaytadan kiriting:",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(context.user_data, get_message)
        )
        return WAITING_FORGOT_CONFIRM

    phone = context.user_data.get('forgot_phone')
    otp = context.user_data.get('forgot_otp')
    
    loading_msg = await update.message.reply_text("⏳ Parol yangilanmoqda...")

    success, data = await backend_client.reset_password(phone, otp, new_password, confirm_password)
    
    if success:
        user_id = str(update.effective_user.id)
        users = _read_json(USERS_JSON_FILE, [])
        
        # Mahalliy foydalanuvchi ma'lumotlarini yangilash
        if isinstance(users, list):
            found = False
            for u in users:
                if str(u.get("user_id")) == user_id:
                    u["vigo_phone"] = phone
                    u["vigo_password"] = new_password
                    found = True
                    break
            if not found:
                users.append({"user_id": int(user_id), "vigo_phone": phone, "vigo_password": new_password})
        elif isinstance(users, dict):
            if user_id not in users:
                users[user_id] = {"user_id": int(user_id)}
            users[user_id]["vigo_phone"] = phone
            users[user_id]["vigo_password"] = new_password
            
        _write_json(USERS_JSON_FILE, users)

        # Token keshini tozalash va yangi parol bilan avtologin qilish
        if user_id in backend_client.user_tokens:
            del backend_client.user_tokens[user_id]
        await backend_client._login_user(user_id)

        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await context.bot.edit_message_text(
            "🎉 <b>Parolingiz muvaffaqiyatli o'zgartirildi!</b>\n\n"
            "Tizimga yangi parolingiz bilan ulandingiz. Endi bot xizmatlaridan to'liq foydalanishingiz mumkin.",
            chat_id=update.effective_chat.id,
            message_id=loading_msg.message_id,
            parse_mode="HTML"
        )
        await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
        return ConversationHandler.END
    else:
        err_text = str(data)
        logger.error(f"reset_password failed: {err_text}")
        
        if "Invalid OTP" in err_text or "otp" in err_text.lower():
            await context.bot.edit_message_text(
                "❌ <b>Tasdiqlash kodi (OTP) noto'g'ri yoki muddati tugagan!</b>\n\n"
                "Iltimos, kodni tekshirib qaytadan kiriting:",
                chat_id=update.effective_chat.id,
                message_id=loading_msg.message_id,
                parse_mode="HTML"
            )
            return WAITING_FORGOT_OTP
        else:
            reply_markup = get_auth_keyboard(context.user_data, get_message)
            await context.bot.edit_message_text(
                f"❌ <b>Xatolik yuz berdi:</b>\n{err_text[:150]}\n\nIltimos, boshidan urinib ko'ring.",
                chat_id=update.effective_chat.id,
                message_id=loading_msg.message_id,
                parse_mode="HTML"
            )
            await update.message.reply_text("Bosh menyu", reply_markup=reply_markup)
            return ConversationHandler.END

def get_forgot_password_conversation_handler():
    from language_handler import MESSAGES
    entry_buttons = [MESSAGES[lang].get("forgot_password_button") for lang in MESSAGES if "forgot_password_button" in MESSAGES[lang]]
    
    return ConversationHandler(
        entry_points=[
            CommandHandler("forgot_password", start_forgot_password),
            MessageHandler(filters.Text(entry_buttons), start_forgot_password),
            CallbackQueryHandler(start_forgot_password, pattern="^start_forgot_pw$")
        ],
        states={
            WAITING_FORGOT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_forgot_phone)],
            WAITING_FORGOT_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_forgot_otp)],
            WAITING_FORGOT_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_forgot_password)],
            WAITING_FORGOT_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_forgot_confirm)],
        },
        fallbacks=[
            CommandHandler("cancel", lambda u, c: ConversationHandler.END)
        ]
    )

