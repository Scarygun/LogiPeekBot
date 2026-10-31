import logging
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, PreCheckoutQueryHandler, MessageHandler, filters, CallbackQueryHandler
from config import PAYMENT_PROVIDER_TOKEN, MONTHLY_SUB_PRICE_UZS
from database import add_subscription_days

logger = logging.getLogger(__name__)

async def send_invoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchiga to'lov chekini yuborish."""
    # Callback query yoki oddiy xabardan chaqirilganini aniqlaymiz
    if update.callback_query:
        chat_id = update.effective_chat.id
        await update.callback_query.answer()
    else:
        chat_id = update.effective_message.chat_id
        
    user_id = update.effective_user.id
    
    if not PAYMENT_PROVIDER_TOKEN:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ To'lov tizimi hozircha ishlamayapti (Token kiritilmagan)."
        )
        return
        
    title = "1 Oylik Obuna"
    description = "LogiPeek tizimidan 30 kun davomida cheklovsiz qidiruv huquqi."
    
    # Payload format: sub_{user_id}_30
    payload = f"sub_{user_id}_30"
    
    currency = "UZS"
    
    # Click (UZS) uchun narx tiyinda kiritilishi kerak
    # 50 000 so'm = 5000000 tiyin
    price_tiyin = int(MONTHLY_SUB_PRICE_UZS) * 100 
    prices = [LabeledPrice("1 Oylik Obuna (LogiPeek)", price_tiyin)]

    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency=currency,
            prices=prices,
            start_parameter="monthly-subscription"
        )
    except Exception as e:
        logger.error(f"Invoice yuborishda xatolik: {e}")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Kvitansiya yuborishda xatolik yuz berdi.")

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov jarayonidagi tasdiq (Telegram so'raydi, bot javob berishi kerak)."""
    query = update.pre_checkout_query
    
    if query.invoice_payload.startswith("sub_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Noto'g'ri to'lov so'rovi.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov muvaffaqiyatli amalga oshganda ishlaydi."""
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment
    payload = payment_info.invoice_payload
    
    logger.info(f"Muvaffaqiyatli to'lov qabul qilindi! User ID: {user_id}, Payload: {payload}")
    
    if payload.startswith("sub_"):
        parts = payload.split('_')
        if len(parts) >= 3:
            days = int(parts[2])
            
            # 30 kun qo'shish
            from datetime import datetime
            new_end = await add_subscription_days(user_id, days)
            end_date = datetime.fromisoformat(new_end)
            formatted_date = end_date.strftime("%Y-%m-%d %H:%M")
            
            await update.message.reply_text(
                f"✅ <b>To'lov muvaffaqiyatli qabul qilindi!</b>\n\n"
                f"Sizga {days} kunlik obuna berildi.\n"
                f"Obunangiz <b>{formatted_date}</b> gacha faol.\n\n"
                f"Endi bemalol yuk izlashingiz mumkin!",
                parse_mode="HTML"
            )
            return

    await update.message.reply_text("✅ To'lov qabul qilindi, ammo tizimda nimadir xato ketdi. Iltimos admin bilan bog'laning.")

def get_payment_handlers():
    """Bot.py uchun handlerlarni qaytarish"""
    return [
        CommandHandler("buy", send_invoice_command),
        CallbackQueryHandler(send_invoice_command, pattern="^buy_sub$"),
        PreCheckoutQueryHandler(precheckout_callback),
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    ]
