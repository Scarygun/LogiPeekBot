import asyncio
import logging
from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler
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
            # Natijalarni context ga saqlash
            context.user_data['search_results'] = results
            context.user_data['search_from_city'] = from_city
            context.user_data['search_to_city'] = to_city
            context.user_data['search_page'] = 0
            
            # Birinchi 10 ta natijani ko'rsatish
            await show_search_results(update, context, page=0)
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

# Natijalarni ko'rsatish funksiyasi
async def show_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Natijalarni sahifalab ko'rsatish - bitta xabarda"""
    results = context.user_data.get('search_results', [])
    from_city = context.user_data.get('search_from_city', '')
    to_city = context.user_data.get('search_to_city', '')
    
    if not results:
        return
    
    RESULTS_PER_PAGE = 10
    total_pages = (len(results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    start_idx = page * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, len(results))
    page_results = results[start_idx:end_idx]
    
    # Xabar yuborish funksiyasi (callback query yoki oddiy xabar uchun)
    if update.callback_query:
        send_message = update.callback_query.message.reply_text
        edit_message = update.callback_query.message.edit_text
    else:
        send_message = update.message.reply_text
        edit_message = None
    
    # Barcha natijalarni bitta xabarda yaratish
    message_text = ""
    
    # Sarlavha
    if page == 0 and not update.callback_query:
        message_text += get_message(context.user_data, "search_results_found", count=len(results), from_city=from_city, to_city=to_city) + "\n\n"
    else:
        message_text += f"🔍 **{from_city} ➡️ {to_city}**\n"
        message_text += f"📊 Jami: {len(results)} ta natija\n\n"
    
    # Natijalarni qo'shish
    for i, result in enumerate(page_results, start=start_idx + 1):
        full_text = result['text']
        display_text = full_text[:200]  # Qisqartirildi
        ellipsis = '...' if len(full_text) > 200 else ''
        
        message_text += f"**#{i} {result['group_title']}**\n"
        message_text += f"📅 {result['date']} | 👤 {result['sender']}\n"
        message_text += f"💬 {display_text}{ellipsis}\n"
        message_text += f"🔗 [Xabarni ko'rish]({result['link']})\n\n"
    
    # Inline button tugmalarini yaratish
    keyboard = []
    
    # Navigation tugmalar - faqat "Oldingi" va "Keyingi"
    nav_row = []
    
    # Oldingi tugmasi (agar birinchi sahifa bo'lmasa)
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"search_page_{page-1}"))
    
    # Yopish tugmasi
    nav_row.append(InlineKeyboardButton("❌ Yopish", callback_data="search_close"))
    
    # Keyingi tugmasi (agar oxirgi sahifa bo'lmasa)
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Keyingi ▶️", callback_data=f"search_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Sahifa ma'lumoti (ixtiyoriy)
    page_info = f"📄 Sahifa {page+1}/{total_pages} | {start_idx+1}-{end_idx} / {len(results)}"
    keyboard.append([InlineKeyboardButton(page_info, callback_data="search_page_info")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Xabarni yuborish yoki yangilash
    try:
        if update.callback_query and edit_message:
            # Callback query bo'lsa, xabarni yangilash
            await edit_message(
                text=message_text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        else:
            # Yangi xabar yuborish
            await send_message(
                text=message_text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Xabar yuborishda xatolik: {e}")
        # Fallback - oddiy matn
        await send_message(
            f"🔍 {from_city} ➡️ {to_city}\n\n" + 
            "\n".join([f"#{i+1} {r['group_title']}" for i, r in enumerate(page_results)]),
            reply_markup=reply_markup
        )

# Callback query handler - sahifa o'zgartirish va natijani ko'rish
async def handle_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sahifa o'zgartirish va natijani ko'rish uchun callback handler"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    logger.debug(f"Search callback data: {callback_data}")
    
    if callback_data == "search_close":
        # Xabarni o'chirish
        try:
            await query.message.delete()
        except Exception as e:
            logger.error(f"Xabarni o'chirishda xatolik: {e}")
        return
    
    if callback_data == "search_page_info":
        # Faqat ma'lumot, hech narsa qilmaymiz
        return
    
    if callback_data.startswith("search_page_"):
        try:
            page_str = callback_data.replace("search_page_", "")
            page = int(page_str)
            logger.debug(f"Sahifa o'zgartirilmoqda: {page}")
            context.user_data['search_page'] = page
            
            # Yangi natijalarni ko'rsatish
            await show_search_results(update, context, page=page)
            
        except (ValueError, IndexError) as e:
            logger.error(f"Sahifa o'zgartirishda xatolik: {e}, callback_data: {callback_data}")
            await query.answer("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.", show_alert=True)
    
    elif callback_data.startswith("search_view_"):
        try:
            result_idx_str = callback_data.replace("search_view_", "")
            result_idx = int(result_idx_str)
            results = context.user_data.get('search_results', [])
            
            logger.debug(f"Natija ko'rsatilmoqda: {result_idx}, jami natijalar: {len(results)}")
            
            if 0 <= result_idx < len(results):
                result = results[result_idx]
                full_text = result['text']
                
                # To'liq natijani ko'rsatish
                detail_message = f"**#{result_idx + 1} {result['group_title']}**\n\n"
                detail_message += f"📅 **Sana:** {result['date']}\n"
                detail_message += f"👤 **Yuboruvchi:** {result['sender']}\n\n"
                detail_message += f"💬 **Xabar:**\n{full_text}\n\n"
                detail_message += f"🔗 [Xabarni ko'rish]({result['link']})"
                
                await query.message.reply_text(
                    detail_message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
            else:
                await query.answer("Natija topilmadi", show_alert=True)
                
        except (ValueError, IndexError) as e:
            logger.error(f"Natijani ko'rishda xatolik: {e}, callback_data: {callback_data}")
            await query.answer("Xatolik yuz berdi", show_alert=True)
    else:
        logger.warning(f"Noma'lum callback_data: {callback_data}")
        await query.answer("Noma'lum buyruq", show_alert=True)

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
        fallbacks=[] # Fallbacks olib tashlandi
    )
