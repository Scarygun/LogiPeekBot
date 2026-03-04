import asyncio
import re
import json
import logging
import time
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from telethon.errors import (
    FloodWaitError, 
    ChatWriteForbiddenError, 
    UserBannedInChannelError, 
    ChannelPrivateError, 
    UsernameNotOccupiedError,
    UsernameInvalidError,
    SlowModeWaitError,
    ChatGuestSendForbiddenError,
    AuthKeyError,
    UserNotParticipantError
)

from language_handler import get_message
from database import get_all_groups, load_groups_from_json
from config import ADMINS, ACTIVE_GROUPS_JSON_FILE
from telethon_client import telethon_client

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BroadcastStates:
    RECEIVE_MESSAGE = 1
    SELECT_ACTION = 2
    SELECT_FREQUENCY = 3
    SELECT_DURATION = 4
    CONFIRM_BROADCAST = 5


FREQUENCY_OPTIONS = {
    "Har 30 daqiqa": 1800,
    "Har 1 soat": 3600,
    "Har 3 soat": 10800,
    "Har 6 soat": 21600,
}

DURATION_OPTIONS = {
    "6 soat": 21600,
    "12 soat": 43200,
    "1 kun": 86400,
    "2 kun": 172800,
}

faol_rassilkalar = {}
active_groups_lock = asyncio.Lock()
ACTIVE_GROUPS_PATH = Path(ACTIVE_GROUPS_JSON_FILE)


def is_broadcast_active(admin_id: int) -> bool:
    state = faol_rassilkalar.get(admin_id)
    return bool(state and state.get("active"))


async def load_active_groups() -> list:
    def _load() -> list:
        if not ACTIVE_GROUPS_PATH.exists():
            return []
        try:
            with ACTIVE_GROUPS_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            logger.warning("active_groups.json ni o'qishda xatolik. Bo'sh ro'yxat qaytarilmoqda.")
        return []

    return await asyncio.to_thread(_load)


async def save_active_groups(groups: list) -> None:
    def _save(items: list) -> None:
        with ACTIVE_GROUPS_PATH.open("w", encoding="utf-8") as f:
            json.dump(items, f, indent=4, ensure_ascii=False)

    async with active_groups_lock:
        await asyncio.to_thread(_save, groups)


async def get_target_groups() -> list:
    """
    JSON fayldan (groups.json) guruhlarni o'qib, xabar yuborish uchun qaytaradi.
    Returns: list of group links
    """
    # To'g'ridan-to'g'ri groups.json dan guruhlarni o'qiyamiz
    logger.info("Groups.json faylidan guruhlar o'qilmoqda...")
    groups_data = await load_groups_from_json()
    
    if not groups_data:
        logger.warning("⚠️ Groups.json faylida guruh topilmadi!")
        return []
    
    # Agar array formatida bo'lsa (oddiy ro'yxat)
    if isinstance(groups_data, list):
        # Faqat string linklarni olamiz
        group_links = [link for link in groups_data if isinstance(link, str) and link.strip()]
        if group_links:
            logger.info(f"✅ Groups.json dan (array format) {len(group_links)} ta guruh topildi.")
            logger.debug(f"Birinchi 5 ta guruh: {group_links[:5]}")
            return group_links
    
    # Agar dict formatida bo'lsa (eski format)
    if isinstance(groups_data, dict):
        group_links = []
        for group_key, group_data in groups_data.items():
            if isinstance(group_data, dict) and 'group_link' in group_data:
                group_link = group_data['group_link']
                if group_link and isinstance(group_link, str):
                    group_links.append(group_link)
            elif isinstance(group_data, str):
                # Agar to'g'ridan-to'g'ri link bo'lsa
                group_links.append(group_data)
        
        if group_links:
            logger.info(f"✅ Groups.json dan (dict format) {len(group_links)} ta guruh topildi.")
            logger.debug(f"Birinchi 5 ta guruh: {group_links[:5]}")
            return group_links

    logger.warning("⚠️ Groups.json faylida guruh topilmadi!")
    return []


async def sleep_with_cancel(seconds: float, admin_id: int, step: float = 1.0) -> None:
    remaining = float(seconds)
    while remaining > 0 and is_broadcast_active(admin_id):
        interval = min(step, remaining)
        await asyncio.sleep(interval)
        remaining -= interval


def normalize_target(group_id):
    """
    Guruh ID yoki linkini tozalash va target formatiga o'tkazish.
    Telethon to'g'ridan-to'g'ri linklarni qabul qiladi, shuning uchun linklarni o'zgartirmasdan qaytaramiz.
    Returns: (target, display_name) tuple
    """
    if isinstance(group_id, str):
        cleaned = group_id.strip()
        # Agar to'liq link bo'lsa, uni to'g'ridan-to'g'ri qaytaramiz (Telethon qabul qiladi)
        if cleaned.startswith("https://t.me/") or cleaned.startswith("http://t.me/"):
            # Linkdan username ni ajratib olish (display_name uchun)
            parts = cleaned.rstrip("/").split("/")
            if len(parts) > 0:
                username = parts[-1]
                # @ belgisini olib tashlash
                if username.startswith("@"):
                    username = username[1:]
                # Telethon to'g'ridan-to'g'ri linkni qabul qiladi
                return cleaned, username
        elif cleaned.startswith("t.me/"):
            # t.me/username formatini https:// ga o'tkazamiz
            username = cleaned.replace("t.me/", "").replace("@", "").strip()
            full_link = f"https://t.me/{username}"
            return full_link, username
        elif cleaned.startswith("@"):
            # @username formatini linkga o'tkazamiz
            username = cleaned[1:].strip()
            full_link = f"https://t.me/{username}"
            return full_link, username
        else:
            # To'g'ridan-to'g'ri username bo'lishi mumkin
            # Agar link formatida bo'lmasa, username sifatida qabul qilamiz
            if "/" not in cleaned and " " not in cleaned:
                # Username bo'lishi mumkin
                full_link = f"https://t.me/{cleaned}"
                return full_link, cleaned
            else:
                # Boshqa format, o'zgartirmasdan qaytaramiz
                return cleaned, cleaned
    
    # Integer yoki boshqa format bo'lsa, o'zgartirmasdan qaytarish
    return group_id, str(group_id)


async def check_group_access(target, display_name):
    """
    Guruhga kirish va yozish huquqini tekshirish (user akkaunt orqali).
    Returns: (can_access, error_message) tuple
    can_access: True - kirish mumkin, False - kirish mumkin emas, None - tekshirish mumkin emas
    """
    try:
        # Guruhni olishga harakat qilish (user akkaunt orqali)
        entity = await telethon_client.client.get_entity(target)
        
        # User akkauntning guruhdagi permissions ni tekshirish
        try:
            me = await telethon_client.client.get_me()
            permissions = await telethon_client.client.get_permissions(entity, me)
            
            # Yozish huquqini tekshirish
            if hasattr(permissions, 'send_messages') and not permissions.send_messages:
                return False, "User akkaunt guruhda yozish huquqiga ega emas (restricted yoki faqat adminlar yozishi mumkin)"
            
            # Agar permissions olingan bo'lsa va yozish huquqi bor bo'lsa
            return True, None
            
        except Exception as perm_error:
            # Permissions olishda xato bo'lsa, user akkaunt guruhga qo'shilmagan bo'lishi mumkin
            logger.debug(f"Permissions olishda xato ({display_name}): {perm_error}")
            # Lekin entity olingan bo'lsa, user akkaunt guruhni ko'ra oladi
            # Yozish huquqini tekshirish uchun xabar yuborishga harakat qilish kerak
            return None, None  # Tekshirish mumkin emas, xabar yuborishga harakat qilish kerak
            
    except UsernameNotOccupiedError:
        return False, "Guruh topilmadi"
    except UsernameInvalidError:
        return False, "Guruh topilmadi"
    except ChannelPrivateError:
        return False, "Guruh private yoki user akkaunt qo'shilmagan"
    except UserNotParticipantError:
        return False, "User akkaunt guruhga a'zo emas"
    except Exception as e:
        # Boshqa xatolarni tekshirish uchun qoldiramiz
        logger.debug(f"Guruh tekshirishda xato ({display_name}): {e}")
        return None, None  # None - tekshirish mumkin emas, xabar yuborishga harakat qilish kerak


async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"start_broadcast called by user {update.effective_user.id}")
    if not update.effective_user or not await is_admin(update.effective_user.id):
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        return ConversationHandler.END
    
    context.user_data.pop("broadcast_data", None)
    await update.message.reply_text(
        get_message(context.user_data, "broadcast_start_message"),
        reply_markup=ReplyKeyboardRemove(),
    )
    return BroadcastStates.RECEIVE_MESSAGE


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = update.message.text
    logger.info(f"receive_message called. User ID: {update.effective_user.id}, Message Text: {message_text}")
    context.user_data["broadcast_data"] = {
        "text": message_text,
    }
    start_text = get_message(context.user_data, "broadcast_start_button")
    stop_text = get_message(context.user_data, "broadcast_stop_button")
    keyboard = [
        [KeyboardButton(start_text)],
        [KeyboardButton(stop_text)],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        get_message(context.user_data, "broadcast_action_prompt"),
        reply_markup=reply_markup,
    )
    return BroadcastStates.SELECT_ACTION


async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    start_text = get_message(context.user_data, "broadcast_start_button")
    stop_text = get_message(context.user_data, "broadcast_stop_button")

    if choice == start_text:
        keyboard = [[KeyboardButton(option)] for option in FREQUENCY_OPTIONS]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            get_message(context.user_data, "broadcast_frequency_prompt"),
            reply_markup=reply_markup,
        )
        return BroadcastStates.SELECT_FREQUENCY

    if choice == stop_text:
        await stop_broadcast_command(update, context)
        keyboard = [
            [KeyboardButton(start_text)],
            [KeyboardButton(stop_text)],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            get_message(context.user_data, "broadcast_action_prompt"),
            reply_markup=reply_markup,
        )
        return BroadcastStates.SELECT_ACTION

    keyboard = [
        [KeyboardButton(start_text)],
        [KeyboardButton(stop_text)],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        get_message(context.user_data, "invalid_choice"),
        reply_markup=reply_markup,
    )
    return BroadcastStates.SELECT_ACTION


async def select_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    logger.debug(f"select_frequency: {choice}")
    if choice not in FREQUENCY_OPTIONS:
        await update.message.reply_text(get_message(context.user_data, "invalid_choice"))
        return BroadcastStates.SELECT_FREQUENCY

    context.user_data.setdefault("broadcast_data", {})["frequency"] = {
        "label": choice,
        "seconds": FREQUENCY_OPTIONS[choice],
    }

    keyboard = [[KeyboardButton(option)] for option in DURATION_OPTIONS]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(get_message(context.user_data, "broadcast_duration_prompt"), reply_markup=reply_markup)
    return BroadcastStates.SELECT_DURATION


async def select_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    logger.debug(f"select_duration: {choice}")
    if choice not in DURATION_OPTIONS:
        await update.message.reply_text(get_message(context.user_data, "invalid_choice"))
        return BroadcastStates.SELECT_DURATION

    context.user_data.setdefault("broadcast_data", {})["duration"] = {
        "label": choice,
        "seconds": DURATION_OPTIONS[choice],
    }

    target_groups = await get_target_groups()
    if not target_groups:
        await update.message.reply_text(get_message(context.user_data, "broadcast_no_groups"))
        context.user_data.pop("broadcast_data", None)
        return ConversationHandler.END

    context.user_data["broadcast_data"]["groups"] = target_groups

    keyboard = [[KeyboardButton(get_message(context.user_data, "confirm_button"))]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    data = context.user_data["broadcast_data"]
    confirm_message = get_message(
        context.user_data,
        "broadcast_confirm_message",
        message=data["text"],
        frequency=data["frequency"]["label"],
        duration=data["duration"]["label"],
        group_count=len(target_groups),
    )
    await update.message.reply_text(confirm_message, reply_markup=reply_markup)
    return BroadcastStates.CONFIRM_BROADCAST


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    logger.info(f"confirm_broadcast called. User ID: {update.effective_user.id}, Choice: {choice}")
    if choice != get_message(context.user_data, "confirm_button"):
        await update.message.reply_text(get_message(context.user_data, "invalid_choice"))
        return BroadcastStates.CONFIRM_BROADCAST

    await launch_broadcast(update, context)
    return ConversationHandler.END


async def launch_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.user_data.get("broadcast_data")
    if not data:
        await update.message.reply_text(get_message(context.user_data, "broadcast_error"))
        return

    admin_id = update.effective_user.id
    if is_broadcast_active(admin_id):
        await update.message.reply_text(get_message(context.user_data, "broadcast_already_running"))
        return

    try:
        if not telethon_client.is_connected():
            await telethon_client.connect()
    except Exception as e:
        logger.error(f"Telethon client ulanishida xato: {e}")
        await update.message.reply_text(get_message(context.user_data, "broadcast_error"))
        return

    language = context.user_data.get("language", "uz")
    user_context = {"language": language}

    groups = data["groups"]
    frequency_seconds = data["frequency"]["seconds"]
    duration_seconds = data["duration"]["seconds"]

    faol_rassilkalar[admin_id] = {"active": True}

    start_message = get_message(
        user_context,
        "broadcast_started",
        group_count=len(groups),
        frequency=data["frequency"]["label"],
    )
    await update.message.reply_text(start_message)

    task = context.application.create_task(
        xabar_yuborish(
            admin_id=admin_id,
            message=data["text"],
            frequency_seconds=frequency_seconds,
            duration_seconds=duration_seconds,
            groups=groups,
            context=context,
            user_context=user_context,
        )
    )
    faol_rassilkalar[admin_id]["task"] = task
    context.user_data.pop("broadcast_data", None)


async def xabar_yuborish(
    admin_id: int,
    message: str,
    frequency_seconds: int,
    duration_seconds: int,
    groups: list,
    context: ContextTypes.DEFAULT_TYPE,
    user_context: dict,
) -> None:
    start_time = time.monotonic()
    successful_groups = []
    iteration = 0
    total_sent = 0
    total_failed = 0

    try:
        # User akkaunt ma'lumotlarini olish
        try:
            me = await telethon_client.client.get_me()
            logger.info(f"👤 User akkaunt: {me.first_name} (@{me.username if me.username else 'username yoq'})")
        except Exception as e:
            logger.warning(f"User akkaunt ma'lumotlarini olishda xato: {e}")
        
        logger.info(f"📤 Xabar yuborish boshlandi. Jami {len(groups)} ta guruhga xabar yuboriladi (JSON fayldan).")
        logger.info(f"📋 Xabar matni: {message[:50]}..." if len(message) > 50 else f"📋 Xabar matni: {message}")
        logger.info(f"🔄 Chastota: har {frequency_seconds} sekundda")
        logger.info(f"⏳ Davomiylik: {duration_seconds} sekund")
        logger.info(f"ℹ️  Eslatma: Xabarlar user akkaunt orqali yuboriladi (bot guruhga qo'shilish shart emas)")
        
        while is_broadcast_active(admin_id):
            iteration += 1
            elapsed = time.monotonic() - start_time
            if elapsed >= duration_seconds:
                logger.info("⏰ Davomiylik muddati tugadi.")
                break

            # Har bir iteratsiya boshida statistika
            logger.info(f"\n🚀 === {iteration}-iteratsiya: {len(groups)} ta guruhga yuborish boshlandi ===")
            
            sent_count = 0
            failed_count = 0
            failed_groups = []

            for group in groups:
                if not is_broadcast_active(admin_id):
                    break
                
                target, display_name = normalize_target(group)
                
                # Guruhni yuborishdan oldin tekshirish (user akkaunt orqali)
                check_result, check_error = await check_group_access(target, display_name)
                if check_result is False:
                    # Guruhga kirish mumkin emas
                    logger.warning(f"❌ @{display_name}: {check_error}")
                    failed_count += 1
                    failed_groups.append((display_name, check_error))
                    await sleep_with_cancel(0.3, admin_id, step=0.3)
                    continue
                elif check_result is None:
                    # Tekshirish mumkin emas, xabar yuborishga harakat qilish kerak
                    logger.debug(f"⚠️  Guruh tekshirish mumkin emas, xabar yuborishga harakat qilinmoqda: @{display_name}")
                
                retry = True
                while retry and is_broadcast_active(admin_id):
                    try:
                        # User akkaunt orqali xabar yuborish
                        # target - bu to'liq link yoki username bo'lishi mumkin
                        await telethon_client.client.send_message(target, message)
                        sent_count += 1
                        successful_groups.append(group)
                        logger.info(f"✅ Yuborildi: @{display_name}")
                        retry = False
                        await sleep_with_cancel(0.5, admin_id, step=0.5)
                    except (FloodWaitError, SlowModeWaitError) as e:
                        wait_seconds = getattr(e, "seconds", getattr(e, "value", 0))
                        logger.warning(f"FloodWait/SlowMode {wait_seconds}s for {display_name}")
                        if wait_seconds:
                            flood_message = get_message(
                                user_context,
                                "broadcast_in_progress_flood",
                                target=display_name,
                                wait=wait_seconds,
                            )
                            await context.bot.send_message(chat_id=admin_id, text=flood_message)
                            await sleep_with_cancel(wait_seconds, admin_id, step=5.0)
                        else:
                            retry = False
                    except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError, ChatGuestSendForbiddenError) as e:
                        error_msg = str(e).lower()
                        if "can't write" in error_msg or "write forbidden" in error_msg:
                            error_reason = "User akkaunt guruhga yozish huquqiga ega emas"
                        elif "not a member" in error_msg or "not in chat" in error_msg:
                            error_reason = "User akkaunt guruhga a'zo emas"
                        elif "banned" in error_msg:
                            error_reason = "User akkaunt guruhda bloklangan"
                        elif "private" in error_msg:
                            error_reason = "Guruh private yoki user akkaunt qo'shilmagan"
                        elif "forbidden" in error_msg:
                            error_reason = "User akkaunt guruhga yozish huquqiga ega emas"
                        else:
                            error_reason = f"Xato: {str(e)[:60]}"
                        
                        logger.warning(f"❌ @{display_name}: {error_reason}")
                        failed_count += 1
                        failed_groups.append((display_name, error_reason))
                        retry = False
                        await sleep_with_cancel(0.3, admin_id, step=0.3)
                        
                    except (UsernameNotOccupiedError, UsernameInvalidError) as e:
                        # Username mavjud emas yoki noto'g'ri format
                        error_reason = "Guruh topilmadi yoki noto'g'ri format"
                        logger.warning(f"❌ @{display_name}: {error_reason}")
                        failed_count += 1
                        failed_groups.append((display_name, error_reason))
                        retry = False
                        await sleep_with_cancel(0.3, admin_id, step=0.3)
                        
                    except AuthKeyError as e:
                        # Auth key muammosi (masalan, RPCError 406: ALLOW_PAYMENT_REQUIRED)
                        error_reason = f"Auth error: {str(e)[:50]}"
                        logger.warning(f"❌ @{display_name}: {error_reason}")
                        failed_count += 1
                        failed_groups.append((display_name, error_reason))
                        retry = False
                        await sleep_with_cancel(0.3, admin_id, step=0.3)
                        
                    except Exception as e:
                        # Boshqa barcha xatolarni umumiy qilib boshqarish
                        error_type = type(e).__name__
                        error_reason = f"{error_type}: {str(e)[:50]}"
                        logger.warning(f"❌ @{display_name}: {error_reason}")
                        failed_count += 1
                        failed_groups.append((display_name, error_reason))
                        retry = False
                        await sleep_with_cancel(0.3, admin_id, step=0.3)

            # Har bir iteratsiyadan keyin natijalarni ko'rsatish (BotPy struktura)
            total_sent += sent_count
            total_failed += failed_count
            
            logger.info(f"\n📊 === {iteration}-iteratsiya natijasi ===")
            logger.info(f"✅ Muvaffaqiyatli: {sent_count} ta")
            logger.info(f"❌ Xatoliklar: {failed_count} ta")
            logger.info(f"📈 Jami: {len(groups)} ta guruh")
            
            if failed_groups:
                logger.info(f"\n❌ Xatoliklar ro'yxati:")
                for group_name, reason in failed_groups[:10]:  # Faqat birinchi 10 tasini ko'rsatish
                    logger.info(f"   • @{group_name} — {reason}")
                if len(failed_groups) > 10:
                    logger.info(f"   ... va yana {len(failed_groups) - 10} ta xatolik")
            
            if sent_count == 0 and failed_count > 0:
                logger.warning(f"\n💡 Maslahat:")
                logger.warning(f"   User akkauntni guruhlarga qo'shing va yozish huquqini bering")
                logger.warning(f"   Yoki guruh sozlamalarida barcha a'zolarga yozish huquqini bering")

            if not is_broadcast_active(admin_id):
                break

            logger.info(f"\n💤 Keyingi yuborish {frequency_seconds} sekunddan so'ng...\n")
            await sleep_with_cancel(frequency_seconds, admin_id, step=5.0)
    finally:
        faol_rassilkalar.pop(admin_id, None)
        total = total_sent + total_failed
        logger.info(f"\n📊 === Yuborish yakunlandi ===")
        logger.info(f"✅ Jami muvaffaqiyatli: {total_sent} ta")
        logger.info(f"❌ Jami xatoliklar: {total_failed} ta")
        logger.info(f"📈 Jami urinishlar: {total} ta")
        logger.info(f"🔄 Jami iteratsiyalar: {iteration} ta")
        
        if total_sent == 0:
            logger.warning("⚠️ Hech qanday xabar muvaffaqiyatli yuborilmadi!")
            # To'g'ridan-to'g'ri xabar yuborish
            no_success_message = f"⚠️ Hech qanday xabar muvaffaqiyatli yuborilmadi.\n❌ Xato: {total_failed} ta guruh\n📊 Jami urinishlar: {total}"
            await context.bot.send_message(chat_id=admin_id, text=no_success_message)
        
        summary_message = get_message(
            user_context,
            "broadcast_success",
            sent=total_sent,
            failed=total_failed,
            total=total,
        )
        await context.bot.send_message(chat_id=admin_id, text=summary_message)

        if successful_groups:
            unique_groups = list(dict.fromkeys(successful_groups))
            await save_active_groups(unique_groups)
            saved_message = get_message(
                user_context,
                "broadcast_saved_groups",
                count=len(unique_groups),
            )
            await context.bot.send_message(chat_id=admin_id, text=saved_message)


async def stop_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text(get_message(context.user_data, "admin_not_authorized"))
        return

    state = faol_rassilkalar.get(user_id)
    if not state or not state.get("active"):
        await update.message.reply_text(get_message(context.user_data, "broadcast_not_running"))
        return

    state["active"] = False
    await update.message.reply_text(get_message(context.user_data, "broadcast_stopped"))


def get_broadcast_conversation_handler() -> ConversationHandler:
    from keyboards import get_all_menu_buttons
    all_buttons = get_all_menu_buttons(get_message)
    btn_pattern = "|".join([re.escape(b) for b in all_buttons])
    buttons_regex = f"^({btn_pattern})$"
    
    from language_handler import MESSAGES
    broadcast_pattern = "|".join([re.escape(MESSAGES[lang]["broadcast_message_button"]) for lang in MESSAGES])
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(f"^({broadcast_pattern})$"),
                start_broadcast,
            )
        ],
        states={
            BroadcastStates.RECEIVE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), receive_message)],
            BroadcastStates.SELECT_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), select_action)],
            BroadcastStates.SELECT_FREQUENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), select_frequency)],
            BroadcastStates.SELECT_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), select_duration)],
            BroadcastStates.CONFIRM_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(buttons_regex), confirm_broadcast)],
        },
        fallbacks=[],
    )


async def is_admin(user_id):
    return user_id in ADMINS
