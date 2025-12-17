import asyncio
import logging
from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.ext import ConversationHandler
from telegram.error import NetworkError
from states import SearchStates
from telethon_client import telethon_client
from language_handler import get_message

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import html

# Yuk qidirishni boshlash
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not telethon_client or not telethon_client.is_connected():
        await update.message.reply_text(
            get_message(context.user_data, "search_error_telethon_not_connected"),
            parse_mode="HTML"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        get_message(context.user_data, "search_from_city_prompt"), 
        parse_mode="HTML"
    )
    return SearchStates.WAITING_FROM

# Qayerdan qidirishni olish
async def process_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_city = update.message.text.strip()
    context.user_data['from_city'] = from_city
    
    await update.message.reply_text(
        get_message(context.user_data, "search_to_city_prompt"), 
        parse_mode="HTML"
    )
    return SearchStates.WAITING_TO

# Progress callback funksiyasi
async def progress_callback(current_count, total_count, current_results, update, context, loading_msg):
    """Har 20 guruhdan keyin topilgan yuklarni yuborish va progress xabarini yangilash"""
    try:
        from_city = context.user_data.get('from_city', '')
        to_city = context.user_data.get('to_city', '')
        
        # Oldingi natijalarni olamiz (takrorlanishni oldini olish uchun)
        previous_results = context.user_data.get('previous_progress_results', [])
        previous_result_ids = {r.get('link', '') + str(r.get('date', '')) for r in previous_results}
        
        # Yangi topilgan natijalarni ajratamiz
        new_results = []
        for result in current_results:
            result_id = result.get('link', '') + str(result.get('date', ''))
            if result_id not in previous_result_ids:
                new_results.append(result)
        
        # Agar yangi natijalar topilgan bo'lsa, ularni yuboramiz
        if new_results:
            # Oldingi natijalarni yangilaymiz
            context.user_data['previous_progress_results'] = current_results.copy()
            
            # Barcha yangi natijalarni yuborish (bir nechta xabarga bo'lib, agar kerak bo'lsa)
            MAX_MESSAGE_LENGTH = 4000  # Telegram xabar limiti 4096, xavfsizlik uchun 4000
            current_message = f"🔍 <b>{html.escape(from_city)} ➡️ {html.escape(to_city)}</b>\n\n"
            current_message += f"✅ <b>{len(new_results)} ta yangi yuk topildi!</b>\n\n"
            
            result_counter = 0
            for result in new_results:
                full_text = result.get('text', '')
                display_text = full_text[:200] if len(full_text) > 200 else full_text
                ellipsis = '...' if len(full_text) > 200 else ''
                
                # Har bir natija uchun matn
                result_text = f'<b>#{result_counter + 1} {html.escape(result.get("group_title", "Noma\'lum"))}</b>\n'
                result_text += f'📅 {html.escape(str(result.get("date", "")))} | 👤 {html.escape(result.get("sender", "Noma\'lum"))}\n'
                result_text += f"💬 {html.escape(display_text)}{ellipsis}\n"
                if result.get('link') and result.get('link') != '#':
                    result_text += f"🔗 <a href=\"{result.get('link')}\">Xabarni ko'rish</a>\n"
                result_text += "\n"
                
                # Agar yangi natija qo'shilsa, xabar juda uzun bo'lishini tekshiramiz
                if len(current_message) + len(result_text) > MAX_MESSAGE_LENGTH:
                    # Joriy xabarni yuboramiz
                    try:
                        await update.message.reply_text(
                            current_message,
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                    except Exception as e:
                        logger.error(f"Natijalarni yuborishda xatolik: {e}")
                    
                    # Yangi xabarni boshlaymiz
                    current_message = f"🔍 <b>{html.escape(from_city)} ➡️ {html.escape(to_city)}</b> (davomi)\n\n"
                
                current_message += result_text
                result_counter += 1
            
            # Oxirgi xabarni yuborish (agar mavjud bo'lsa)
            if current_message.strip() and current_message.strip() != f"🔍 <b>{html.escape(from_city)} ➡️ {html.escape(to_city)}</b>\n\n":
                try:
                    await update.message.reply_text(
                        current_message,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Natijalarni yuborishda xatolik: {e}")
        
        # Progress xabarini yangilash
        progress_text = (
            f"⏳ <b>Qidiruv davom etmoqda...</b>\n\n"
            f"📍 {html.escape(from_city)} ➡️ {html.escape(to_city)}\n\n"
            f"📊 Tekshirilmoqda: {current_count}/{total_count} guruh\n"
            f"✅ Jami topildi: {len(current_results)} ta yuk"
        )
        
        progress_message_id = context.user_data.get('progress_message_id')
        
        # Agar progress xabari mavjud bo'lsa, uni yangilaymiz
        if progress_message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=progress_message_id,
                    text=progress_text,
                    parse_mode="HTML"
                )
            except Exception:
                # Agar xabarni yangilab bo'lmasa, yangi xabar yuboramiz
                context.user_data['progress_message_id'] = None
                progress_message_id = None
        
        # Agar progress xabari yo'q bo'lsa, yangi yaratamiz
        if not progress_message_id:
            try:
                # Loading xabarini o'chirib, progress xabarini yuboramiz
                if loading_msg:
                    try:
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=loading_msg.message_id
                        )
                    except:
                        pass
                
                sent_msg = await update.message.reply_text(
                    progress_text,
                    parse_mode="HTML"
                )
                context.user_data['progress_message_id'] = sent_msg.message_id
            except Exception as e:
                logger.error(f"Progress xabarini yuborishda xatolik: {e}")
    except Exception as e:
        logger.error(f"Progress callback da xatolik: {e}")

# Qayerga qidirishni olish va natijalarni ko'rsatish
async def process_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Yangi qidiruv boshida progress xabarini va oldingi natijalarni tozalaymiz
    context.user_data['progress_message_id'] = None
    context.user_data['previous_progress_results'] = []
    
    to_city = update.message.text.strip()
    from_city = context.user_data.get('from_city', '')
    
    # Yuklash xabarini yuborish
    loading_msg = await update.message.reply_text(
        get_message(context.user_data, "search_in_progress", from_city=from_city, to_city=to_city),
        parse_mode="HTML"
    )
    
    # Progress callback funksiyasini yaratamiz
    async def progress_cb(current_count, total_count, current_results):
        await progress_callback(current_count, total_count, current_results, update, context, loading_msg)
    
    try:
        # Telethon orqali qidiruvni amalga oshirish
        results = await telethon_client.search_messages(from_city, to_city, progress_callback=progress_cb)
        
        # Progress xabarini o'chirish
        progress_message_id = context.user_data.get('progress_message_id')
        if progress_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id, 
                    message_id=progress_message_id
                )
            except:
                pass
        
        # Loading xabarini o'chirish (agar hali o'chirilmagan bo'lsa)
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, 
                message_id=loading_msg.message_id
            )
        except:
            pass
        
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
                parse_mode="HTML"
            )
    
    except Exception as e:
        logger.error(f"Qidiruvda xatolik: {e}")
        # Progress xabarini o'chirish
        progress_message_id = context.user_data.get('progress_message_id')
        if progress_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id, 
                    message_id=progress_message_id
                )
            except:
                pass
        await update.message.reply_text(
            get_message(context.user_data, "search_error_unexpected")
        )
    finally:
        # Tozalash
        context.user_data.pop('progress_message_id', None)
        context.user_data.pop('previous_progress_results', None)
    
    return ConversationHandler.END

# Natijalarni ko'rsatish funksiyasi
async def show_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Natijalarni sahifalab ko'rsatish - bitta xabarda"""
    results = context.user_data.get('search_results', [])
    from_city = context.user_data.get('search_from_city', '')
    to_city = context.user_data.get('search_to_city', '')
    
    if not results:
        return
    
    RESULTS_PER_PAGE = 100  # Har bir sahifada 100 ta natija ko'rsatish
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
    
    # Telegram xabar uzunligi cheklovi (4096 belgi, xavfsizlik uchun 4000)
    MAX_MESSAGE_LENGTH = 4000
    
    # Barcha natijalarni bitta yoki bir nechta xabarda yaratish
    messages = []  # Bir nechta xabar bo'lishi mumkin
    current_message = ""
    
    # Sarlavha
    header = ""
    if page == 0 and not update.callback_query:
        header = get_message(context.user_data, "search_results_found", count=len(results), from_city=from_city, to_city=to_city) + "\n\n"
    else:
        header = f"🔍 <b>{html.escape(from_city)} ➡️ {html.escape(to_city)}</b>\n"
        header += f"📊 Jami: {len(results)} ta natija | Sahifa: {page + 1}/{total_pages}\n\n"
    
    current_message = header
    
    # Natijalarni qo'shish
    for i, result in enumerate(page_results, start=start_idx + 1):
        full_text = result['text']
        display_text = full_text[:150]  # Qisqartirildi (100 ta natija uchun)
        ellipsis = '...' if len(full_text) > 150 else ''
        
        result_text = f"<b>#{i} {html.escape(result['group_title'])}</b>\n"
        result_text += f"📅 {html.escape(str(result['date']))} | 👤 {html.escape(result['sender'])}\n"
        result_text += f"💬 {html.escape(display_text)}{ellipsis}\n"
        if result.get('link') and result.get('link') != '#':
            result_text += f"🔗 <a href=\"{result['link']}\">Xabarni ko'rish</a>\n"
        result_text += "\n"
        
        # Agar yangi natija qo'shilsa, xabar juda uzun bo'lishini tekshiramiz
        if len(current_message) + len(result_text) > MAX_MESSAGE_LENGTH:
            # Joriy xabarni saqlaymiz
            messages.append(current_message)
            # Yangi xabarni boshlaymiz (sarlavhasiz)
            current_message = f"🔍 <b>{html.escape(from_city)} ➡️ {html.escape(to_city)}</b> (davomi)\n\n"
        
        current_message += result_text
    
    # Oxirgi xabarni qo'shamiz
    if current_message.strip() and current_message.strip() != header.strip():
        messages.append(current_message)
    
    # Agar hech qanday xabar yaratilmagan bo'lsa, kamida sarlavhani yuboramiz
    if not messages:
        messages.append(header + "📋 Natijalar topilmadi yoki xabar yaratib bo'lmadi.")
    
    # Inline button tugmalarini yaratish
    keyboard = []
    
    # Navigation tugmalar - faqat "Oldingi" va "Keyingi"
    nav_row = []
    
    # Oldingi tugmasi (agar birinchi sahifa bo'lmasa)
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"search_page_{page-1}"))
    
    # Keyingi tugmasi (agar oxirgi sahifa bo'lmasa)
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Keyingi ▶️", callback_data=f"search_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Xabarlarni yuborish yoki yangilash
    try:
        if update.callback_query and edit_message:
            # Callback query bo'lsa, birinchi xabarni yangilash
            if messages:
                await edit_message(
                    text=messages[0],
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
                # Qolgan xabarlarni alohida yuborish
                for msg in messages[1:]:
                    try:
                        await send_message(
                            text=msg,
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                    except Exception as e:
                        logger.error(f"Qo'shimcha xabar yuborishda xatolik: {e}")
        else:
            # Yangi xabarlarni yuborish
            for i, msg in enumerate(messages):
                # Birinchi xabarga tugmalarni qo'shamiz
                markup = reply_markup if i == 0 else None
                try:
                    await send_message(
                        text=msg,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                        reply_markup=markup
                    )
                except Exception as e:
                    logger.error(f"Xabar yuborishda xatolik: {e}")
    except Exception as e:
        logger.error(f"Xabar yuborishda xatolik: {e}")
        # Fallback - oddiy matn
        try:
            await send_message(
                f"🔍 {from_city} ➡️ {to_city}\n\n" + 
                "\n".join([f"#{i+1} {r['group_title']}" for i, r in enumerate(page_results[:50])]),  # 50 tagacha ko'rsatish
                reply_markup=reply_markup
            )
        except Exception as fallback_err:
            logger.error(f"Fallback xabar yuborishda xatolik: {fallback_err}")

# Callback query handler - sahifa o'zgartirish va natijani ko'rish
async def handle_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sahifa o'zgartirish va natijani ko'rish uchun callback handler"""
    query = update.callback_query
    
    # Callback query javobini yuborish (tarmoq xatolarini boshqarish)
    try:
        await query.answer()
    except NetworkError as e:
        logger.warning(f"Tarmoq xatosi: callback query javobini yuborib bo'lmadi: {e}")
        # Tarmoq xatosi bo'lsa ham, handler davom etishi kerak
    except Exception as e:
        logger.error(f"Callback query javobida kutilmagan xatolik: {e}")
    
    callback_data = query.data
    logger.debug(f"Search callback data: {callback_data}")
    
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
            try:
                await query.answer("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.", show_alert=True)
            except (NetworkError, Exception) as err:
                logger.warning(f"Xatolik xabarini yuborib bo'lmadi: {err}")
    
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
                detail_message = f"<b>#{result_idx + 1} {html.escape(result['group_title'])}</b>\n\n"
                detail_message += f"📅 <b>Sana:</b> {html.escape(str(result['date']))}\n"
                detail_message += f"👤 <b>Yuboruvchi:</b> {html.escape(result['sender'])}\n\n"
                detail_message += f"💬 <b>Xabar:</b>\n{html.escape(full_text)}\n\n"
                detail_message += f"🔗 <a href=\"{result['link']}\">Xabarni ko'rish</a>"
                
                await query.message.reply_text(
                    detail_message,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            else:
                try:
                    await query.answer("Natija topilmadi", show_alert=True)
                except (NetworkError, Exception) as err:
                    logger.warning(f"Xatolik xabarini yuborib bo'lmadi: {err}")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Natijani ko'rishda xatolik: {e}, callback_data: {callback_data}")
            try:
                await query.answer("Xatolik yuz berdi", show_alert=True)
            except (NetworkError, Exception) as err:
                logger.warning(f"Xatolik xabarini yuborib bo'lmadi: {err}")
    else:
        logger.warning(f"Noma'lum callback_data: {callback_data}")
        try:
            await query.answer("Noma'lum buyruq", show_alert=True)
        except (NetworkError, Exception) as err:
            logger.warning(f"Xatolik xabarini yuborib bo'lmadi: {err}")

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
