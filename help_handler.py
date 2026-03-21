import logging
import re
from telegram import Update, MessageEntity
from telegram.ext import ConversationHandler, MessageHandler, filters, ContextTypes, CommandHandler
from language_handler import get_message
from keyboards import get_main_menu_keyboard, get_back_keyboard
from config import SUPPORT_GROUP_ID

logger = logging.getLogger(__name__)

# State definitions
HELP_TEXT = 1

async def help_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.info(f"Yordam so'rovi boshlandi: User {user.id} ({user.full_name})")
    full_name = user.full_name
    
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        get_message(context.user_data, "help_start", full_name=full_name),
        reply_markup=reply_markup
    )
    return HELP_TEXT

async def help_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_message = update.message.text
    user = update.effective_user
    logger.info(f"Yordam xabari olindi: User {user.id} - '{user_message}'")
    from language_handler import is_back_button
    if is_back_button(user_message):
        logger.info(f"Yordam so'rovi bekor qilindi (Orqaga bosildi): User {user.id}")
        # Return to main menu
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await update.message.reply_text(
            get_message(context.user_data, "help_cancelled"), # Or just return to main menu message
            reply_markup=reply_markup
        )
        # Show main menu message as well
        await update.message.reply_text(
            get_message(context.user_data, "main_menu"),
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    # Forward message to support group
    try:
        # Create a formatted message for the group
        admin_text = (
            f"👤 \u200E<a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
            f"🆔 <code>{user.id}</code>\n"
            f"@{user.username if user.username else 'No username'}\n\n"
            f"📝 {user_message}"
        )
        
        logger.info(f"Support guruhiga xabar yuborilmoqda: {SUPPORT_GROUP_ID}")
        await context.bot.send_message(
            chat_id=SUPPORT_GROUP_ID,
            text=admin_text,
            parse_mode='HTML'
        )
        logger.info("Xabar muvaffaqiyatli forward qilindi")
        
        # Confirm for user
        reply_markup = get_back_keyboard(context.user_data, get_message)
        await update.message.reply_text(
            get_message(context.user_data, "help_forwarded"),
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Help xabarini forward qilishda xatolik: {e}", exc_info=True)
        if "Chat not found" in str(e):
            await update.message.reply_text(
                "⚠️ <b>Xatolik:</b> Support guruhi topilmadi.\n\n"
                "Iltimos, bot admini bilan bog'laning yoki guruh ID raqamini tekshiring.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("Xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.")
        return HELP_TEXT

    return HELP_TEXT

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
            HELP_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), help_received)]
        },
        fallbacks=[]
    )

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin guruhidan yozilgan javobni foydalanuvchiga yuborish."""
    
    # DEBUG LOGS
    chat_id = update.effective_chat.id
    msg = update.message
    # logger.info(f"Admin reply handler triggered. Chat ID: {chat_id}, Is Reply: {bool(msg.reply_to_message)}")
    
    # Faqat support guruhidan va reply bo'lgan xabarlarni qabul qilamiz
    if chat_id != SUPPORT_GROUP_ID or not msg.reply_to_message:
        # logger.info(f"Target miss: ChatID match={chat_id == SUPPORT_GROUP_ID}, IsReply={bool(msg.reply_to_message)}")
        return

    logger.info(f"Support guruhidan javob aniqlandi: Message ID {msg.message_id}")
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
