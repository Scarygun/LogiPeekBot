import logging
import re
from datetime import datetime
from telegram import Update, MessageEntity, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
from language_handler import get_message, is_back_button
from keyboards import get_main_menu_keyboard, get_back_keyboard, get_all_menu_buttons
from config import OWNER_ID
from backend_client import backend_client

logger = logging.getLogger(__name__)

# State definitions
STATE_SUPPORT_MENU = 1
STATE_WRITING_MESSAGE = 2
STATE_REQUESTING_CALLBACK = 3

def get_support_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Yangi xabar yozish", callback_data="supp_write")],
        [InlineKeyboardButton("📜 Yozishmalar tarixi", callback_data="supp_history"), InlineKeyboardButton("🔄 Yangilash", callback_data="supp_refresh")],
        [InlineKeyboardButton("📞 Qo'ng'iroqqa buyurtma berish", callback_data="supp_callback")],
        [InlineKeyboardButton("🔙 Bosh menyu", callback_data="supp_close")]
    ])

async def build_support_menu_text(user_id: str, user_name: str) -> str:
    conv = await backend_client.get_support_conversation(user_id)
    msg_count = 0
    is_resolved = False
    
    if conv and isinstance(conv, dict):
        messages = conv.get("messages", [])
        msg_count = len(messages)
        is_resolved = conv.get("resolved", False)
        
    status_text = "⚪️ Yangi murojaat" if msg_count == 0 else ("🔴 Yopilgan" if is_resolved else "🟢 Faol muloqot")
    
    text = (
        "💬 <b>Qo'llab-quvvatlash va Yordam markazi</b>\n\n"
        f"Hurmatli <b>{user_name}</b>, ushbu bo'lim orqali operatorlarimiz bilan to'g'ridan-to'g'ri muloqot qilishingiz mumkin.\n\n"
        f"📊 <b>Chat holati:</b> {status_text}\n"
        f"✉️ <b>Xabarlar soni:</b> {msg_count} ta\n\n"
        "<i>Quyidagi tugmalardan birini tanlang:</i>"
    )
    return text

async def help_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_id = str(user.id)
    logger.info(f"Yordam bo'limi ochildi: User {user.id} ({user.full_name})")
    
    text = await build_support_menu_text(user_id, user.full_name)
    reply_markup = get_support_menu_keyboard()
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return STATE_SUPPORT_MENU

async def supp_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    user_id = str(user.id)
    
    if data == "supp_refresh":
        text = await build_support_menu_text(user_id, user.full_name)
        await query.message.edit_text(text, reply_markup=get_support_menu_keyboard(), parse_mode="HTML")
        return STATE_SUPPORT_MENU

    elif data == "supp_history":
        conv = await backend_client.get_support_conversation(user_id)
        messages = []
        if conv and isinstance(conv, dict):
            messages = conv.get("messages", [])
            
        if not messages:
            hist_text = "📜 <b>Yozishmalar tarixi</b>\n\n<i>Siz hali qo'llab-quvvatlash xizmati bilan yozishmagansiz.</i>"
        else:
            hist_text = "📜 <b>Yozishmalar tarixi:</b>\n\n"
            # Ko'rsatish uchun so'nggi 10 ta xabarni olamiz
            for m in messages[-10:]:
                sent_by_staff = m.get("sent_by_staff", False)
                if sent_by_staff:
                    sender_name = "👨‍💼 Operator"
                else:
                    sender_name = "👤 Siz"
                    
                msg_body = m.get("message") or m.get("text") or ""
                created_at = m.get("created_at", "")
                time_str = ""
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        time_str = f" [{dt.strftime('%H:%M')}]"
                    except:
                        pass
                hist_text += f"{sender_name}{time_str}:\n{msg_body}\n\n"
                
        keyboard = [
            [InlineKeyboardButton("✍️ Yangi xabar yozish", callback_data="supp_write")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="supp_back")]
        ]
        await query.message.edit_text(hist_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return STATE_SUPPORT_MENU

    elif data == "supp_write":
        text = (
            "✍️ <b>Savol yoki murojaatingizni yozing:</b>\n\n"
            "Murojaatingiz to'g'ridan-to'g'ri administrator va operatorga yetkaziladi."
        )
        keyboard = [[InlineKeyboardButton("🔙 Bekor qilish", callback_data="supp_back")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return STATE_WRITING_MESSAGE

    elif data == "supp_callback":
        text = (
            "📞 <b>Qayta qo'ng'iroqqa buyurtma berish</b>\n\n"
            "Iltimos, operatorimiz siz bilan bog'lanishi uchun telefon raqamingizni kiriting:\n"
            "<i>(Masalan: +998901234567)</i>"
        )
        keyboard = [[InlineKeyboardButton("🔙 Bekor qilish", callback_data="supp_back")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return STATE_REQUESTING_CALLBACK

    elif data == "supp_back":
        text = await build_support_menu_text(user_id, user.full_name)
        await query.message.edit_text(text, reply_markup=get_support_menu_keyboard(), parse_mode="HTML")
        return STATE_SUPPORT_MENU

    elif data == "supp_close":
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await query.message.delete()
        await query.message.chat.send_message(
            get_message(context.user_data, "main_menu"),
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    return STATE_SUPPORT_MENU

async def supp_message_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_message = update.message.text.strip()
    user = update.effective_user
    user_id = str(user.id)
    
    # 1. Backend Support Chatga yuborish
    res = await backend_client.send_support_message(user_message, user_id)
    
    # 2. Owner/Admin chatiga ham forward qilish (tezkor xabardor bo'lishi uchun)
    try:
        admin_text = (
            f"💬 <b>Yangi Support Xabari:</b>\n\n"
            f"👤 <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
            f"🆔 <code>{user.id}</code>\n"
            f"@{user.username if user.username else 'No username'}\n\n"
            f"📝 {user_message}"
        )
        await context.bot.send_message(chat_id=OWNER_ID, text=admin_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Xabarni ownerga forward qilishda xatolik: {e}")
        
    # Foydalanuvchiga tasdiq
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Yozishmalar tarixini ko'rish", callback_data="supp_history")],
        [InlineKeyboardButton("✍️ Yana xabar yozish", callback_data="supp_write")],
        [InlineKeyboardButton("🔙 Bosh menyu", callback_data="supp_close")]
    ])
    await update.message.reply_text(
        "✅ <b>Xabaringiz qabul qilindi!</b>\n\nOperatorlarimiz tez orada javob qaytarishadi.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return STATE_SUPPORT_MENU

async def supp_callback_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone_number = update.message.text.strip()
    user = update.effective_user
    user_id = str(user.id)
    
    # Backendga callback request yuborish
    await backend_client.request_support_callback(phone=phone_number, message=f"Telegram User: {user.full_name} (@{user.username})", user_id=user_id)
    
    # Ownerga bildirishnoma
    try:
        admin_text = (
            f"📞 <b>Qo'ng'iroqqa buyurtma!</b>\n\n"
            f"👤 {user.full_name} (@{user.username if user.username else 'No username'})\n"
            f"🆔 <code>{user.id}</code>\n"
            f"📱 Telefon: <code>{phone_number}</code>"
        )
        await context.bot.send_message(chat_id=OWNER_ID, text=admin_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ownerga callback xabarini yuborishda xatolik: {e}")
        
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Yordam menyusiga qaytish", callback_data="supp_back")],
        [InlineKeyboardButton("🔙 Bosh menyu", callback_data="supp_close")]
    ])
    await update.message.reply_text(
        f"✅ <b>Rahmat!</b> Sizning telefon raqamingiz (<code>{phone_number}</code>) qabul qilindi. Tez orada siz bilan bog'lanamiz.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return STATE_SUPPORT_MENU

async def handle_menu_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Foydalanuvchi bosh menyu tugmasini bosganida chiroyli chiqib ketish"""
    return ConversationHandler.END

def get_help_conversation_handler() -> ConversationHandler:
    from keyboards import get_all_menu_buttons
    all_buttons = get_all_menu_buttons(get_message)
    btn_pattern = "|".join([re.escape(b) for b in all_buttons])
    buttons_regex = f"^({btn_pattern})$"
    
    from language_handler import MESSAGES
    entry_buttons = [MESSAGES[lang]["help_button"] for lang in MESSAGES]
    
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(entry_buttons), help_start),
            CommandHandler("help", help_start),
        ],
        states={
            STATE_SUPPORT_MENU: [
                CallbackQueryHandler(supp_menu_callback, pattern="^supp_")
            ],
            STATE_WRITING_MESSAGE: [
                CallbackQueryHandler(supp_menu_callback, pattern="^supp_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), supp_message_received)
            ],
            STATE_REQUESTING_CALLBACK: [
                CallbackQueryHandler(supp_menu_callback, pattern="^supp_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), supp_callback_received)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex(buttons_regex), handle_menu_exit),
            CallbackQueryHandler(supp_menu_callback, pattern="^supp_close$")
        ],
        per_message=False,
        name="help_support_conv"
    )

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin guruhidan yozilgan javobni foydalanuvchiga yuborish."""
    
    # DEBUG LOGS
    chat_id = update.effective_chat.id
    msg = update.message
    # logger.info(f"Admin reply handler triggered. Chat ID: {chat_id}, Is Reply: {bool(msg.reply_to_message)}")
    
    # Faqat ownerdan va reply bo'lgan xabarlarni qabul qilamiz
    if chat_id != OWNER_ID or not msg.reply_to_message:
        # logger.info(f"Target miss: ChatID match={chat_id == OWNER_ID}, IsReply={bool(msg.reply_to_message)}")
        return

    logger.info(f"Ownerdan javob aniqlandi: Message ID {msg.message_id}")
    reply_to = msg.reply_to_message
    
    # User ID ni entitylardan qidirish
    user_id = None
    entities = reply_to.entities or reply_to.caption_entities or []
    
    for entity in entities:
        if entity.type == MessageEntity.TEXT_MENTION and entity.user:
            user_id = entity.user.id
            logger.info(f"User ID topildi (Text Mention): {user_id}")
            break
        elif entity.type == MessageEntity.TEXT_LINK and entity.url:
            # Check for tg://user?id=123 format
            match = re.match(r"tg://user\?id=(\d+)", entity.url)
            if match:
                user_id = int(match.group(1))
                logger.info(f"User ID topildi (Text Link): {user_id}")
                break
    
    if user_id:
        logger.info(f"Javob User {user_id} ga yuborilmoqda...")
        
        try:
            # Admindan kelgan javobni foydalanuvchiga yuborish
            await context.bot.send_message(
                chat_id=user_id,
                text=f"<b>Javob:</b>\n\n{msg.text}",
                parse_mode='HTML'
            )
            logger.info("Javob foydalanuvchiga muvaffaqiyatli yetkazildi")
            
            # Adminga tasdiq yuborish - OLIB TASHLANDI
            # await msg.reply_text("✅ Javob foydalanuvchiga yuborildi.")
        except Exception as e:
            logger.error(f"Javob yuborishda xatolik: {e}", exc_info=True)
            await msg.reply_text(f"❌ Xatolik: {e}")
    else:
        logger.warning(f"User ID topilmadi! Message entities: {entities}")
        # Agar ID topilmasa
        return
