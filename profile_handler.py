import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler
from language_handler import get_message
from database import _read_json, _write_json
from config import USERS_JSON_FILE

logger = logging.getLogger(__name__)

async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    users = _read_json(USERS_JSON_FILE, [])
    vigo_phone = "Noma'lum"
    vigo_password = None
    
    if isinstance(users, list):
        for u in users:
            if str(u.get("user_id")) == user_id:
                vigo_phone = u.get("vigo_phone", "Noma'lum")
                vigo_password = u.get("vigo_password")
                break
    elif isinstance(users, dict):
        if user_id in users:
            vigo_phone = users[user_id].get("vigo_phone", "Noma'lum")
            vigo_password = users[user_id].get("vigo_password")
            
    # Backenddan ma'lumot olish
    backend_info = ""
    from backend_client import backend_client
    import aiohttp
    
    token = await backend_client._get_valid_token(user_id)
    if token:
        try:
            me_url = f"{backend_client.base_url}/api/v1/auth/me/"
            headers = {"Authorization": f"Bearer {token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(me_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        full_name = data.get("full_name", "Noma'lum")
                        role = data.get("role", "Noma'lum")
                        
                        role_emoji = "🚗" if role == "driver" else "📦"
                        role_text = "Haydovchi" if role == "driver" else ("Yuk egasi" if role == "cargo_owner" else role)
                        
                        is_verified = data.get("is_verified", False)
                        verify_text = "✅ Tasdiqlangan" if is_verified else "⏳ Kutilmoqda"
                        
                        # Aniq profil bo'yicha holatni tekshirish (masalan haydovchi hujjatlari)
                        extra_info = ""
                        if role == "driver" and data.get("driver_profile"):
                            prof = data["driver_profile"]
                            prof_verified = prof.get("verified")
                            if prof_verified == "approved":
                                verify_text = "✅ Tasdiqlangan"
                            elif prof_verified == "pending":
                                verify_text = "⏳ Kutilmoqda (Tekshirilmoqda)"
                            elif prof_verified == "rejected":
                                verify_text = "❌ Rad etilgan"
                                
                            # Mashina ma'lumotlarini olish
                            v_make = prof.get("vehicle_make")
                            v_model = prof.get("vehicle_model")
                            v_number = prof.get("vehicle_number")
                            v_type = prof.get("vehicle_type")
                            v_capacity = prof.get("capacity_kg")
                            
                            car_name = f"{v_make or ''} {v_model or ''}".strip() or "Kiritilmagan"
                            car_number = v_number if v_number else "Kiritilmagan"
                            car_type = v_type if v_type else "Noma'lum"
                            car_cap = f"{v_capacity} kg" if v_capacity else "Noma'lum"
                            
                            extra_info = (
                                f"\n🚛 <b>Mashina:</b> {car_name}\n"
                                f"🔢 <b>Davlat raqami:</b> {car_number}\n"
                                f"📦 <b>Turi / Sig'imi:</b> {car_type} / {car_cap}\n"
                            )
                                
                        elif role == "cargo_owner" and data.get("cargo_owner_profile"):
                            prof_verified = data["cargo_owner_profile"].get("verified")
                            if prof_verified == "approved":
                                verify_text = "✅ Tasdiqlangan"
                            elif prof_verified == "pending":
                                verify_text = "⏳ Kutilmoqda (Tekshirilmoqda)"
                            elif prof_verified == "rejected":
                                verify_text = "❌ Rad etilgan"
                                
                        backend_info = (
                            f"👤 <b>F.I.O:</b> {full_name}\n"
                            f"{role_emoji} <b>Rol:</b> {role_text}\n"
                            f"📝 <b>Profil holati:</b> {verify_text}\n"
                            f"{extra_info}"
                        )
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            
    text = (
        "👤 <b>Mening Profilim</b>\n\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"📞 <b>Telefon raqam:</b> {vigo_phone}\n\n"
        f"{backend_info}\n"
        "<i>Quyidagi menyu orqali profilingizni boshqarishingiz mumkin:</i>\n\n"
        "🔗 <b><a href=\"https://play.google.com/store/apps/details?id=com.vigo.uz\">📱 Mobil ilovani yuklab olish</a></b>"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚪 Tizimdan chiqish", callback_data="profile_logout")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def handle_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "profile_logout":
        user_id = str(update.effective_user.id)
        users = _read_json(USERS_JSON_FILE, [])
        
        modified = False
        if isinstance(users, list):
            for u in users:
                if str(u.get("user_id")) == user_id:
                    if "vigo_phone" in u:
                        del u["vigo_phone"]
                    if "vigo_password" in u:
                        del u["vigo_password"]
                    modified = True
                    break
        elif isinstance(users, dict):
            if user_id in users:
                if "vigo_phone" in users[user_id]:
                    del users[user_id]["vigo_phone"]
                if "vigo_password" in users[user_id]:
                    del users[user_id]["vigo_password"]
                modified = True
                
        if modified:
            _write_json(USERS_JSON_FILE, users)
            
        # Delete the token from backend_client cache
        from backend_client import backend_client
        if user_id in backend_client.user_tokens:
            del backend_client.user_tokens[user_id]
            
        from keyboards import get_auth_keyboard
        reply_markup = get_auth_keyboard(context.user_data, get_message)
        
        await query.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🚪 Tizimdan muvaffaqiyatli chiqdingiz.\n\nBotdan foydalanish uchun qayta Tizimga kiring yoki Ro'yxatdan o'ting.",
            reply_markup=reply_markup
        )

def get_profile_handler():
    from language_handler import MESSAGES
    buttons = [MESSAGES[lang]["profile_button"] for lang in MESSAGES]
    return MessageHandler(filters.Text(buttons), handle_profile)
