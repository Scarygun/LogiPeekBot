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
            reply_markup = get_main_menu_keyboard(context.user_data, get_message)
            await update.message.reply_text(
                get_message(context.user_data, "search_no_results", from_city=from_city, to_city=to_city),
                parse_mode="HTML",
                reply_markup=reply_markup
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
        reply_markup = get_main_menu_keyboard(context.user_data, get_message)
        await update.message.reply_text(
            get_message(context.user_data, "search_error_unexpected"),
            reply_markup=reply_markup
        )
    finally:
        # Tozalash
        context.user_data.pop('progress_message_id', None)
        context.user_data.pop('last_progress_text', None)
        context.user_data.pop('previous_progress_results', None)
        context.user_data.pop('to_city', None)
    
    return ConversationHandler.END

CARGO_TYPE_MAP = {
    'food': "Oziq-ovqat",
    'general': "Umumiy yuk",
    'refrigerated': "Muzlatkich (Ref)",
    'construction': "Qurilish mollari",
    'dangerous': "Xavfli yuk (ADR)",
    'liquid': "Suyuqlik",
    'livestock': "Tirik hayvonlar",
    'auto': "Avtomobil tashish",
    'equipment': "Uskunalar / Texnika",
}

FOOD_SUBTYPE_MAP = {
    'animal': "hayvonot mahsulotlari",
    'plant': "meva-sabzavot / o'simlik",
}

DOC_TYPE_MAP = {
    'passport': "Haydovchi pasporti",
    'driver_license': "Haydovchilik guvohnomasi (Prava)",
    'vehicle_registration': "Avtotransport tex-pasporti",
    'vehicle_insurance': "Sug'urta polisi",
    'vehicle_technical_inspection': "Texnik ko'rik (TOSMOTR)",
    'ttn': "TTN (Tovar-transport yukxati)",
    'invoice': "Hisob-faktura (Invoice)",
    'veterinary_certificate': "Veterinariya sertifikati",
    'phytosanitary_certificate': "Fitosanitariya sertifikati",
    'cmr': "CMR xalqaro yuk xati",
    'tir': "TIR Carnet"
}

def format_weight(weight_val):
    if not weight_val:
        return "Ko'rsatilmagan"
    try:
        w_f = float(weight_val)
        return f"{int(w_f):,} kg".replace(",", " ") if w_f.is_integer() else f"{w_f:,.1f} kg".replace(",", " ")
    except Exception:
        return f"{weight_val} kg"

def format_price(price_val, currency="UZS", negotiable=False):
    if not price_val:
        return "Kelishiladi" if negotiable else "Ko'rsatilmagan"
    try:
        p_f = float(price_val)
        curr = currency or "UZS"
        return f"{int(p_f):,} {curr}".replace(",", " ") if p_f.is_integer() else f"{p_f:,.2f} {curr}".replace(",", " ")
    except Exception:
        return f"{price_val} {currency or ''}"

def format_cargo_type(cargo_type, subtype=None):
    if not cargo_type:
        return "Umumiy yuk"
    base = CARGO_TYPE_MAP.get(str(cargo_type).lower(), str(cargo_type))
    if subtype and str(subtype).lower() in FOOD_SUBTYPE_MAP:
        base += f" ({FOOD_SUBTYPE_MAP[str(subtype).lower()]})"
    elif subtype and str(subtype).lower() not in ('none', 'null', ''):
        base += f" ({subtype})"
    return base

def format_docs_list(listing_docs, driver_docs, general_docs):
    lines = []
    
    cargo_doc_keys = [d for d in (listing_docs or []) if d]
    if cargo_doc_keys:
        names = [DOC_TYPE_MAP.get(k, k) for k in cargo_doc_keys]
        lines.append(f"• <b>Tovarga:</b> {', '.join(names)}")
        
    drv_keys = [d for d in (driver_docs or []) if d]
    if drv_keys:
        names = [DOC_TYPE_MAP.get(k, k) for k in drv_keys]
        lines.append(f"• <b>Haydovchiga:</b> {', '.join(names)}")
        
    if not lines and general_docs:
        names = [DOC_TYPE_MAP.get(k, k) for k in general_docs if k]
        if names:
            lines.append(f"• {', '.join(names)}")
            
    return "\n".join(lines) if lines else "Standart hujjatlar"

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
    
    # 2. Ro'yxatni shakllantirish (Yuk nomi, vazni va narxi)
    for i, result in enumerate(page_results):
        actual_idx = start_idx + i + 1
        item_title = result.get('title') or result.get('group_title', 'Yuk')
        if len(item_title) > 35:
            item_title = item_title[:35] + "..."
            
        weight_str = format_weight(result.get('weight_kg'))
        price_str = format_price(result.get('price'), result.get('currency'), result.get('price_negotiable'))
             
        item_text = (
            f"<b>{actual_idx}.) 📦 {html.escape(item_title)}</b>\n"
            f"⚖️ Vazni: <b>{html.escape(weight_str)}</b>  |  💰 Narxi: <b>{html.escape(price_str)}</b>"
        )
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
                
                title = result.get('title') or result.get('group_title', 'Yuk')
                origin = result.get('origin') or context.user_data.get('search_from_city', '')
                destination = result.get('destination') or context.user_data.get('search_to_city', '')
                
                weight_str = format_weight(result.get('weight_kg'))
                price_str = format_price(result.get('price'), result.get('currency'), result.get('price_negotiable'))
                cargo_type_display = format_cargo_type(result.get('cargo_type'), result.get('food_subtype'))
                
                pickup_date = str(result.get('pickup_date') or result.get('date', ''))
                delivery_date = str(result.get('required_delivery_date') or '')
                sender = result.get('owner_name') or result.get('sender', 'Vigo Tizimi')
                
                docs_text = format_docs_list(
                    result.get('required_listing_document_types'),
                    result.get('required_driver_document_types'),
                    result.get('required_doc_types')
                )
                
                detail_message = f"<b>#{result_idx + 1} {html.escape(title)}</b>\n\n"
                if origin and destination:
                    detail_message += f"📍 <b>Marshrut:</b> {html.escape(origin)} ➡️ {html.escape(destination)}\n"
                detail_message += f"📦 <b>Yuk turi:</b> {html.escape(cargo_type_display)}\n"
                detail_message += f"⚖️ <b>Vazni:</b> {html.escape(weight_str)}\n"
                detail_message += f"💰 <b>Narxi:</b> {html.escape(price_str)}\n"
                detail_message += f"📅 <b>Yuklash sanasi:</b> {html.escape(pickup_date)}\n"
                if delivery_date:
                    detail_message += f"🏁 <b>Yetkazish muddati:</b> {html.escape(delivery_date)}\n"
                detail_message += f"👤 <b>Yuk egasi:</b> {html.escape(sender)}\n\n"
                
                detail_message += f"📑 <b>Talab qilingan hujjatlar:</b>\n{docs_text}\n\n"
                
                desc = result.get('description', '')
                if desc and desc.strip():
                    detail_message += f"💬 <b>Tavsif:</b> {html.escape(desc.strip())}\n\n"
                
                if result.get('link') and result.get('link') != '#':
                    detail_message += f"🔗 <a href=\"{result['link']}\">Vigo tizimida ko'rish</a>\n\n"
                
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
