import asyncio
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler
from telegram.ext import ConversationHandler
from telegram.error import NetworkError
from states import SearchStates
from backend_client import backend_client
from language_handler import get_message
from keyboards import get_main_menu_keyboard, get_back_keyboard

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import html

# Yuk qidirishni boshlash
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):


    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        get_message(context.user_data, "search_from_city_prompt"), 
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return SearchStates.WAITING_FROM

# Qayerdan qidirishni olish
async def process_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    from language_handler import is_back_button
    if is_back_button(text):
        # Bosh menyuga qaytish
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await update.message.reply_text(
            get_message(context.user_data, "main_menu"),
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    from_city = text
    context.user_data['from_city'] = from_city
    
    reply_markup = get_back_keyboard(context.user_data, get_message)
    await update.message.reply_text(
        get_message(context.user_data, "search_to_city_prompt"), 
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return SearchStates.WAITING_TO

# Progress callback funksiyasi
async def progress_callback(current_count, total_count, current_results, update, context, loading_msg):
    """Har 20 guruhdan keyin progress xabarini yangilash"""
    try:
        from_city = context.user_data.get('from_city', '')
        to_city = context.user_data.get('to_city', '')
        
        # Jami topilganlar soni
        progress_text = f"🔍 <b>Qidirilmoqda...</b>\n\n📍 {html.escape(from_city)} ➡️ {html.escape(to_city)}\n\n📊 Jami topildi: {len(current_results)} ta yuk"
        
        # Agar progress xabari allaqachon mavjud bo'lsa, uni tahrirlaymiz
        progress_message_id = context.user_data.get('progress_message_id')
        
        if progress_message_id:
            try:
                # Agar xabar o'zgargan bo'lsa, tahrirlaymiz (Telegram API limitini tejash uchun)
                last_progress_text = context.user_data.get('last_progress_text', '')
                if progress_text != last_progress_text:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=progress_message_id,
                        text=progress_text,
                        parse_mode="HTML"
                    )
                    context.user_data['last_progress_text'] = progress_text
            except Exception:
                # Agar xabar tahrirlashda xatolik bo'lsa (masalan xabar o'chirilgan), yangi xabar yuboramiz
                # Lekin ko'p xatolik bo'lmasligi uchun pass qilamiz yoki log yozamiz
                # logger.warning(f"Progress xabarini tahrirlashda xatolik: {e}")
                pass
        else:
            # Agar loading xabari bo'lsa, uni tahrirlaymiz va progress ID qilib saqlaymiz
            if loading_msg:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=loading_msg.message_id,
                        text=progress_text,
                        parse_mode="HTML"
                    )
                    context.user_data['progress_message_id'] = loading_msg.message_id
                    context.user_data['last_progress_text'] = progress_text
                except Exception:
                    # Agar loading xabarini ham tahrirlab bo'lmasa, yangi xabar yuboramiz
                    try:
                        sent_msg = await update.message.reply_text(
                            progress_text,
                            parse_mode="HTML"
                        )
                        context.user_data['progress_message_id'] = sent_msg.message_id
                        context.user_data['last_progress_text'] = progress_text
                    except Exception as e2:
                        logger.error(f"Progress xabarini yuborishda xatolik: {e2}")

    except Exception as e:
        logger.error(f"Progress callback da xatolik: {e}")

# Qayerga qidirishni olish va natijalarni ko'rsatish
async def process_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    from language_handler import is_back_button
    if is_back_button(text):
        # Oldingi qadamga qaytish (WAITING_FROM)
        reply_markup = get_back_keyboard(context.user_data, get_message)
        await update.message.reply_text(
            get_message(context.user_data, "search_from_city_prompt"),
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return SearchStates.WAITING_FROM

    # Yangi qidiruv boshida progress xabarini va oldingi natijalarni tozalaymiz
    context.user_data['progress_message_id'] = None
    context.user_data['previous_progress_results'] = []
    
    to_city = text
    from_city = context.user_data.get('from_city', '')
    context.user_data['to_city'] = to_city
    
    # Yuklash xabarini yuborish
    loading_msg = await update.message.reply_text(
        get_message(context.user_data, "search_in_progress", from_city=from_city, to_city=to_city),
        parse_mode="HTML"
    )
    
    try:
        # Backend API orqali qidiruvni amalga oshirish
        user_id = str(update.effective_user.id)
        results = await backend_client.search_loads(from_city, to_city, user_id)
        
        if results == "NOT_LOGGED_IN":
            # Xabarni o'chirish
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
            reply_markup = get_main_menu_keyboard(context.user_data, get_message)
            await update.message.reply_text(
                "❌ <b>Siz tizimga kirmagansiz!</b>\n\nIltimos, avval <b>🔑 Tizimga kirish</b> tugmasi orqali Vigo.uz hisobingizga kiring.",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        
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
            
            # Asosiy menyuni ko'rsatamiz (ReplyKeyboardMarkup)
            reply_markup = get_main_menu_keyboard(context.user_data, get_message)
            await update.message.reply_text(
                get_message(context.user_data, "main_menu"),
                reply_markup=reply_markup
            )
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
        context.user_data.pop('last_progress_text', None)
        context.user_data.pop('previous_progress_results', None)
        context.user_data.pop('to_city', None)
    
    return ConversationHandler.END

# Natijalarni ko'rsatish funksiyasi
async def show_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Natijalarni sahifalab ko'rsatish - ro'yxat ko'rinishida"""
    results = context.user_data.get('search_results', [])
    from_city = context.user_data.get('search_from_city', '')
    to_city = context.user_data.get('search_to_city', '')
    
    if not results:
        return
    
    RESULTS_PER_PAGE = 10  # Har bir sahifada 10 ta natija
    total_pages = (len(results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    
    # Sahifa chegarasini tekshirish
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    start_idx = page * RESULTS_PER_PAGE
    end_idx = min(start_idx + RESULTS_PER_PAGE, len(results))
    page_results = results[start_idx:end_idx]
    
    # Xabar yuborish funksiyasi
    if update.callback_query:
        send_message = update.callback_query.message.edit_text
    else:
        send_message = update.message.reply_text
    
    # 1. Header matni
    header = get_message(context.user_data, "search_list_header", 
                         page=page+1, 
                         total=total_pages, 
                         from_city=html.escape(from_city), 
                         to_city=html.escape(to_city),
                         count=len(results))
    
    message_text = header + "\n\n"
    
    # 2. Ro'yxatni shakllantirish
    for i, result in enumerate(page_results):
        actual_idx = start_idx + i + 1
        # Qisqacha nom (guruh nomi yoki birinchi qator)
        group_title = result.get('group_title', 'Noma\'lum')
        # Agar group_title juda uzun bo'lsa qisqartirish
        if len(group_title) > 20:
             group_title = group_title[:20] + "..."
             
        full_text = result.get('text', '')
        # Matnni qisqartirish (masalan 100 belgi)
        snippet = full_text[:100].replace('\n', ' ')
        if len(full_text) > 100:
            snippet += "..."
             
        item_text = get_message(context.user_data, "search_result_item_list", 
                idx=actual_idx, 
                                title=html.escape(group_title),
                                text=html.escape(snippet))
        message_text += item_text + "\n\n"

    message_text += "🔗 <b><a href=\"https://play.google.com/store/apps/details?id=com.vigo.uz\">📱 Mobil ilovani yuklab olish</a></b>"

    # 3. Tugmalarni yaratish
    keyboard = []
    
    # Raqamli tugmalar (1-10)
    # 5 tadan 2 qator
    row1 = []
    row2 = []
    
    for i in range(len(page_results)):
        actual_idx = start_idx + i 
        btn_text = str(actual_idx + 1)
        callback_data = f"search_view_{actual_idx}"
        if i < 5:
            row1.append(InlineKeyboardButton(btn_text, callback_data=callback_data))
        else:
            row2.append(InlineKeyboardButton(btn_text, callback_data=callback_data))
            
    if row1: keyboard.append(row1)
    if row2: keyboard.append(row2)
    
    # Navigatsiya va Bosh menyu tugmalari (bitta qatorda)
    nav_row = []
    
    # Bosh menyu tugmasi (Chapda)
    menu_text = get_message(context.user_data, "main_menu_button")
    nav_row.append(InlineKeyboardButton(menu_text, callback_data="search_menu"))
    
    # Oldingi (O'rtada, agar bor bo'lsa)
    if page > 0:
        nav_text = get_message(context.user_data, "prev_button")
        nav_row.append(InlineKeyboardButton(nav_text, callback_data=f"search_page_{page-1}"))
        
    # Keyingi (O'ngda, agar bor bo'lsa)
    if page < total_pages - 1:
        nav_text = get_message(context.user_data, "next_button")
        nav_row.append(InlineKeyboardButton(nav_text, callback_data=f"search_page_{page+1}"))
        
    keyboard.append(nav_row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await send_message(
            message_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Natijalarni ko'rsatishda xatolik: {e}")
        # Agar edit_text o'xshamasa (masalan xabar o'zgarmagan bo'lsa), yangi xabar yuborishga urinib ko'ramiz
        if update.callback_query:
             try:
                await update.callback_query.message.reply_text(
                    message_text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
             except Exception as e2:
                 logger.error(f"Qayta yuborishda xatolik: {e2}")

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
    
    elif callback_data == "search_menu":
        # Bosh menyuga qaytish va search contextni tozalash
        await query.message.delete() # Xabarni o'chirish
        # Contextni tozalash
        context.user_data.pop('search_results', None)
        context.user_data.pop('search_from_city', None)
        context.user_data.pop('search_to_city', None)
        context.user_data.pop('search_page', None)
        
        # Main menu ni ko'rsatish
        user_lang = context.user_data.get('language', 'uz')
        main_menu_markup = get_main_menu_keyboard({'language': user_lang}, get_message)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=get_message(context.user_data, "main_menu"),
            reply_markup=main_menu_markup
        )

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
                header = get_message(context.user_data, "search_details_header",
                                    idx=result_idx + 1,
                                    title=html.escape(result.get('group_title', 'Noma\'lum')),
                                    date=html.escape(str(result.get('date', ''))),
                                    sender=html.escape(result.get('sender', '')))
                
                detail_message = header
                detail_message += f"💬 {html.escape(full_text)}\n\n"
                if result.get('link') and result.get('link') != '#':
                    detail_message += f"🔗 <a href=\"{result['link']}\">Xabarni ko'rish</a>\n\n"
                
                detail_message += "🔗 <b><a href=\"https://play.google.com/store/apps/details?id=com.vigo.uz\">📱 Mobil ilovani yuklab olish</a></b>"
                
                # Orqaga qaytish tugmasi
                back_button_text = get_message(context.user_data, "back_to_list")
                # Hozirgi sahifani aniqlash
                current_page = context.user_data.get('search_page', 0)
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton(back_button_text, callback_data=f"search_page_{current_page}")]
                ])
                
                await query.message.edit_text(
                    detail_message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
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
    from keyboards import get_all_menu_buttons
    all_buttons = get_all_menu_buttons(get_message)
    btn_pattern = "|".join([re.escape(b) for b in all_buttons])
    buttons_regex = f"^({btn_pattern})$"
    
    from language_handler import MESSAGES
    entry_buttons = [MESSAGES[lang]["search_load"] for lang in MESSAGES]
    
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(entry_buttons), start_search),
            CommandHandler("search", start_search)
        ],
        states={
            SearchStates.WAITING_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), process_from)],
            SearchStates.WAITING_TO: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), process_to)],
        },
        fallbacks=[] # Fallbacks olib tashlandi
    )
