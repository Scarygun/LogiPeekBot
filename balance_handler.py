import logging
import io
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler, ConversationHandler

from database import check_user_subscription, get_user_subscription_end, add_subscription_days
from payment_db import create_payment, get_payment, update_payment_status
from language_handler import get_message, MESSAGES
from config import OWNER_ID
from backend_client import backend_client

logger = logging.getLogger(__name__)

WAITING_PLAN_SELECT = 1
WAITING_UPLOAD_CLICK = 2
WAITING_RECEIPT = 3

# Fallback configs agar backend kartasi vaqtincha sozlanmagan bo'lsa
DEFAULT_PRO_PRICE = "49 000"
DEFAULT_CARD_NUMBER = "8600 **** **** 1234"
DEFAULT_CARD_OWNER = "LogiPeek"

async def handle_check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # 1. Backenddan joriy obunani tekshirishga harakat qilamiz
    backend_sub = await backend_client.get_subscription(user_id)
    is_pro = False
    sub_end_str = None
    days_left = 0
    
    if backend_sub and isinstance(backend_sub, dict):
        status = backend_sub.get("status")
        is_pro = (status == "active")
        sub_end_str = backend_sub.get("end_date") or backend_sub.get("expires_at")
    
    # Agar backendda aniqlanmasa, mahalliy bazani tekshiramiz
    if not is_pro:
        local_active = await check_user_subscription(user_id)
        if local_active:
            is_pro = True
            sub_end_str = await get_user_subscription_end(user_id)
    
    if is_pro and sub_end_str:
        # PRO Tariff
        try:
            end_date_obj = datetime.fromisoformat(sub_end_str.replace("Z", "+00:00"))
            days_left = (end_date_obj.date() - datetime.now().date()).days
            if days_left < 0:
                days_left = 0
            end_date_formatted = end_date_obj.strftime("%d.%m.%Y")
        except Exception:
            end_date_formatted = str(sub_end_str)[:10]
            days_left = 30
            
        text = (
            "🚚 <b>Sizning tarifingiz</b>\n\n"
            "💎 <b>PRO</b>\n\n"
            f"📅 <b>Tugaydi:</b> {end_date_formatted}\n\n"
            f"⏳ <b>Qolgan vaqt:</b> {days_left} kun\n"
        )
        keyboard = [[InlineKeyboardButton("🔄 PRO ni yangilash", callback_data="buy_pro")]]
    else:
        # FREE Tariff
        text = (
            "🚚 <b>Sizning tarifingiz</b>\n\n"
            "🆓 <b>FREE</b>\n\n"
            "💰 <b>Narxi:</b> 0 so'm\n"
            "📅 <b>Muddat:</b> Cheklanmagan\n\n"
            "<i>Asosiy imkoniyatlardan foydalaning.</i>\n\n"
            "💎 <b>LogiPeek PRO tarifiga o'tib kengaytirilgan imkoniyatlardan foydalaning!</b>\n"
            f"Narxi: {DEFAULT_PRO_PRICE} so'm / 30 kun"
        )
        keyboard = [[InlineKeyboardButton("💎 PRO ga o'tish (Sotib olish)", callback_data="buy_pro")]]
        
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return ConversationHandler.END

async def buy_pro_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    
    # 1. Backenddan faol tarif rejalari va to'lov kartasini olamiz
    plans = await backend_client.get_subscription_plans(user_id)
    card_info = await backend_client.get_payment_card(user_id)
    
    card_number = DEFAULT_CARD_NUMBER
    card_holder = DEFAULT_CARD_OWNER
    card_note = ""
    
    if card_info and isinstance(card_info, dict):
        card_number = card_info.get("card_number") or card_info.get("card_number_raw") or card_number
        card_holder = card_info.get("holder_name") or card_info.get("card_holder") or card_holder
        card_note = card_info.get("instructions") or card_info.get("instruction_note") or ""
        bank_name = card_info.get("bank_name")
        if bank_name and bank_name not in card_holder:
            card_holder = f"{card_holder} ({bank_name})"
        
    selected_plan_id = None
    price_display = DEFAULT_PRO_PRICE
    duration_days = 30
    
    if plans and len(plans) > 0:
        # Birinchi mos tarif rejasini tanlaymiz
        plan = plans[0]
        selected_plan_id = plan.get("id")
        plan_name = plan.get("name", "PRO")
        raw_price = plan.get("price")
        if raw_price:
            try:
                price_display = f"{int(float(raw_price)):,}".replace(",", " ")
            except Exception:
                price_display = str(raw_price)
        duration_days = plan.get("duration_days", 30)
    
    # Backendda purchase (to'lov sessiyasi) boshlaymiz agar plan_id bo'lsa
    backend_payment_id = None
    if selected_plan_id:
        purchase_res = await backend_client.purchase_subscription(selected_plan_id, user_id)
        if purchase_res and isinstance(purchase_res, dict):
            backend_payment_id = purchase_res.get("id") or purchase_res.get("payment_id")
    
    context.user_data["pending_payment_id"] = backend_payment_id
    context.user_data["pending_plan_id"] = selected_plan_id
    
    note_text = f"\nℹ️ <i>{card_note}</i>\n" if card_note else ""
    
    text = (
        "💎 <b>LogiPeek PRO</b>\n\n"
        f"💰 <b>Narxi:</b> {price_display} so'm\n"
        f"📅 <b>Muddat:</b> {duration_days} kun\n\n"
        "💳 <b>To'lov uchun karta:</b>\n"
        f"<code>{card_number}</code>\n\n"
        "👤 <b>Qabul qiluvchi:</b>\n"
        f"<code>{card_holder}</code>\n"
        f"{note_text}\n"
        "<b>To'lov tartibi:</b>\n"
        f"1. Yuqoridagi karta raqamiga {price_display} so'm o'tkazing.\n"
        "2. To'lov chekini saqlab oling.\n"
        "3. Quyidagi tugmani bosib chekni yuboring.\n"
        "4. Admin veb paneldan tasdiqlagach, PRO tarifingiz faollashadi.\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("🧾 Chekni yuborish", callback_data="click_upload")],
        [InlineKeyboardButton("🔙 Bekor qilish", callback_data="cancel_payment")]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return WAITING_UPLOAD_CLICK

async def click_upload_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "<i>👇 Iltimos, pastdagi 📎 (skrepka) tugmasi orqali to'lov chekini rasm ko'rinishida shu yerga yuboring.</i>"
    keyboard = [[InlineKeyboardButton("🔙 Bekor qilish", callback_data="cancel_payment")]]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return WAITING_RECEIPT

async def receive_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_file = None
    photo_id = None
    file_name = "receipt.jpg"
    
    if update.message.photo:
        photo = update.message.photo[-1]
        photo_id = photo.file_id
        tg_file = await context.bot.get_file(photo.file_id)
        file_name = "receipt.jpg"
    elif update.message.document:
        doc = update.message.document
        photo_id = doc.file_id
        tg_file = await context.bot.get_file(doc.file_id)
        file_name = doc.file_name or "receipt.jpg"
    else:
        await update.message.reply_text("Iltimos, chekni <b>rasm</b> ko'rinishida yuboring!", parse_mode="HTML")
        return WAITING_RECEIPT
        
    user_id = str(update.effective_user.id)
    full_name = update.effective_user.full_name
    
    backend_payment_id = context.user_data.get("pending_payment_id")
    
    # Mahalliy bazaga yozib qo'yamiz (har qanday holat uchun)
    local_payment_id = await create_payment(
        int(user_id) if user_id.isdigit() else user_id,
        full_name,
        photo_id,
        amount=49000,
        duration_days=30,
        backend_payment_id=backend_payment_id
    )
    
    # Rasmni yuklab olamiz
    file_bytes = None
    if tg_file:
        byte_stream = io.BytesIO()
        await tg_file.download_to_memory(byte_stream)
        file_bytes = byte_stream.getvalue()
    
    # Backendga chekni yuklash
    backend_payment_id = context.user_data.get("pending_payment_id")
    uploaded_to_backend = False
    
    if backend_payment_id and file_bytes:
        success, res = await backend_client.upload_payment_receipt(
            payment_id=backend_payment_id,
            file_bytes=file_bytes,
            filename=file_name,
            user_id=user_id
        )
        if success:
            uploaded_to_backend = True
            logger.info(f"Foydalanuvchi {user_id} cheki backendga muvaffaqiyatli yuklandi: {backend_payment_id}")
        else:
            logger.warning(f"Chekni backendga yuklashda xatolik: {res}")
            
    # Foydalanuvchiga tasdiq xabari
    text = (
        "⏳ <b>To'lovingiz qabul qilindi.</b>\n\n"
        "To'lov admin tomonidan tekshirilmoqda. PRO obunangiz admin paneldan tasdiqlanganidan so'ng faollashadi."
    )
    await update.message.reply_text(text, parse_mode="HTML")
            
    return ConversationHandler.END

async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("To'lov bekor qilindi.")
    return ConversationHandler.END

def get_balance_handler():
    from language_handler import MESSAGES
    balance_buttons = [MESSAGES[lang]["check_balance"] for lang in MESSAGES]
    
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(balance_buttons), handle_check_balance),
            CallbackQueryHandler(buy_pro_callback, pattern="^buy_pro$")
        ],
        states={
            WAITING_UPLOAD_CLICK: [
                CallbackQueryHandler(click_upload_callback, pattern="^click_upload$")
            ],
            WAITING_RECEIPT: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_receipt),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_receipt)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_payment, pattern="^cancel_payment$"),
            MessageHandler(filters.Text(balance_buttons), handle_check_balance)
        ],
        per_message=False,
        name="payment_conv"
    )
    
    return conv_handler

