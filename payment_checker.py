
import asyncio
import logging
from datetime import datetime, timedelta
from database import add_subscription_days
from payment_db import get_pending_backend_payments, update_payment_status
from backend_client import backend_client

logger = logging.getLogger(__name__)

async def payment_checker_job(application):
    """
    Backenddagi to'lovlar statusini davriy tekshirib boruvchi va
    admin tasdiqlaganda foydalanuvchiga Telegramda bildirishnoma yuboruvchi vazifa.
    """
    logger.info("To'lovlarni tekshiruvchi background jarayon ishga tushdi.")
    bot = application.bot
    
    while True:
        try:
            pending_payments = await get_pending_backend_payments()
            if pending_payments:
                for payment in pending_payments:
                    p_id = payment.get("id")
                    b_id = payment.get("backend_payment_id")
                    user_id = payment.get("user_id")
                    duration_days = payment.get("duration_days", 30)
                    
                    if not b_id or not user_id:
                        continue
                        
                    details = await backend_client.get_payment_details(b_id, str(user_id))
                    if not details or not isinstance(details, dict):
                        continue
                        
                    status = details.get("status")
                    
                    if status == "success":
                        # Admin to'lovni tasdiqlagan!
                        logger.info(f"To'lov tasdiqlandi: {b_id} (Foydalanuvchi: {user_id})")
                        await update_payment_status(p_id, "approved")
                        await add_subscription_days(user_id, duration_days)
                        
                        try:
                            msg = (
                                "🎉 <b>Tabriklaymiz! To'lovingiz tasdiqlandi!</b>\n\n"
                                f"💎 Sizning <b>PRO</b> obunangiz <b>{duration_days} kunga</b> faollashtirildi.\n"
                                "Endi botning barcha imkoniyatlaridan to'liq foydalanishingiz mumkin!"
                            )
                            await bot.send_message(chat_id=int(user_id), text=msg, parse_mode="HTML")
                        except Exception as e:
                            logger.error(f"Foydalanuvchiga {user_id} xabar yuborishda xatolik: {e}")
                            
                    elif status in ("failed", "rejected", "cancelled"):
                        # Admin to'lovni rad etgan!
                        rejection_reason = ""
                        latest_receipt = details.get("latest_receipt")
                        if latest_receipt and isinstance(latest_receipt, dict):
                            rejection_reason = latest_receipt.get("rejection_reason") or ""
                            
                        logger.info(f"To'lov rad etildi: {b_id} (Foydalanuvchi: {user_id})")
                        await update_payment_status(p_id, "rejected", reason=rejection_reason)
                        
                        try:
                            reason_text = f"\nSababi: <i>{rejection_reason}</i>\n" if rejection_reason else ""
                            msg = (
                                "❌ <b>To'lovingiz rad etildi!</b>\n"
                                f"{reason_text}\n"
                                "Iltimos, ma'lumotlarni tekshirib qaytadan to'g'ri chek yuboring yoki qo'llab-quvvatlash xizmatiga murojaat qiling."
                            )
                            await bot.send_message(chat_id=int(user_id), text=msg, parse_mode="HTML")
                        except Exception as e:
                            logger.error(f"Foydalanuvchiga {user_id} rad xabari yuborishda xatolik: {e}")
                            
        except Exception as e:
            logger.error(f"payment_checker_job ichida kutilmagan xatolik: {e}")
            
        await asyncio.sleep(15)  # Har 15 soniyada tekshiradi
