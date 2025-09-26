import asyncio
import logging
from telegram import Update, Message
from telegram.ext import ContextTypes, MessageHandler, filters
from telegram.ext import ConversationHandler
from states import SearchStates
from telethon_client import telethon_client
from language_handler import get_message

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Yuk qidirishni boshlash
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not telethon_client or not telethon_client.is_connected():
        await update.message.reply_text(
            get_message(context.user_data, "search_error_telethon_not_connected"),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        get_message(context.user_data, "search_from_city_prompt"), 
        parse_mode="Markdown"
    )
    return SearchStates.WAITING_FROM

# Qayerdan qidirishni olish
async def process_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_city = update.message.text.strip()
    context.user_data['from_city'] = from_city
    
    await update.message.reply_text(
        get_message(context.user_data, "search_to_city_prompt"), 
        parse_mode="Markdown"
    )
    return SearchStates.WAITING_TO

# Qayerga qidirishni olish va natijalarni ko'rsatish
async def process_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    to_city = update.message.text.strip()
    from_city = context.user_data.get('from_city', '')
    
    # Yuklash xabarini yuborish
    loading_msg = await update.message.reply_text(
        get_message(context.user_data, "search_in_progress", from_city=from_city, to_city=to_city),
        parse_mode="Markdown"
    )
    
    try:
        # Telethon orqali qidiruvni amalga oshirish
        results = await telethon_client.search_messages(from_city, to_city)
        
        # Yuklash xabarini o'chirish
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, 
            message_id=loading_msg.message_id
        )
        
        if results:
            await update.message.reply_text(
                get_message(context.user_data, "search_results_found", count=len(results), from_city=from_city, to_city=to_city),
                parse_mode="Markdown"
            )
            
            # Natijalarni chiqarish
            for i, result in enumerate(results[:10], 1):
                full_text = result['text']
                display_text = full_text[:300]
                ellipsis = '...' if len(full_text) > 300 else ''
                
                text_message = get_message(
                    context.user_data, 
                    "search_result_item",
                    i=i,
                    group_title=result['group_title'],
                    date=result['date'],
                    sender=result['sender'],
                    text=display_text,
                    ellipsis=ellipsis,
                    link=result['link']
                )
                
                try:
                    await update.message.reply_text(
                        text_message, 
                        parse_mode="Markdown", 
                        disable_web_page_preview=True
                    )
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Xabar yuborishda xatolik: {e}")
                    await update.message.reply_text(
                        f"#{i} {result['group_title']}\n{result['text'][:200]}..." # Fallback in case of formatting issues
                    )
            
            if len(results) > 10:
                await update.message.reply_text(
                    get_message(context.user_data, "search_more_results", count=len(results)-10)
                )
        else:
            await update.message.reply_text(
                get_message(context.user_data, "search_no_results", from_city=from_city, to_city=to_city),
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Qidiruvda xatolik: {e}")
        await update.message.reply_text(
            get_message(context.user_data, "search_error_unexpected")
        )
    
    return ConversationHandler.END

# Bekor qilish
async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_message(context.user_data, "search_cancelled"))
    return ConversationHandler.END

# Conversation handler yaratish
def get_search_conversation_handler():
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f"^({get_message({'language': 'uz'}, 'search_load')}|{get_message({'language': 'ru'}, 'search_load')})$"), 
                start_search
            )
        ],
        states={
            SearchStates.WAITING_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_from)],
            SearchStates.WAITING_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_to)],
        },
        fallbacks=[
            MessageHandler(
                filters.Regex(f"^({get_message({'language': 'uz'}, 'cancel_button')}|{get_message({'language': 'ru'}, 'cancel_button')}|Cancel)$"), 
                cancel_search
            )
        ],
    )
