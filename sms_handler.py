"""
TextUP SMS yuborish ConversationHandler.

Oqim (admin uchun):
  SMS Yuborish tugmasi
  → Qabul qiluvchi tanlash  (TextUP guruh  |  Telefon raqam)
  → Shablon tanlash          (mavjud shablonlar yoki o'z matningiz)
  → Alpha name tanlash       (ixtiyoriy – agar bir nechta bo'lsa)
  → Tasdiqlash va yuborish

Faqat ADMINS ro'yxatidagi foydalanuvchilar foydalana oladi.
"""

import logging
import re
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import ADMINS, TEXTUP_EMAIL, TEXTUP_PASSWORD
from language_handler import get_message
from textup_client import TextUpClient, TextUpAuthError, TextUpAPIError
from typing import Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Global TextUp client (singleton)
# ------------------------------------------------------------------ #

_textup_client: Optional[TextUpClient] = None


def get_textup_client() -> TextUpClient:
    global _textup_client
    if _textup_client is None:
        _textup_client = TextUpClient(TEXTUP_EMAIL, TEXTUP_PASSWORD)
    return _textup_client


# ------------------------------------------------------------------ #
#  Holatlar
# ------------------------------------------------------------------ #

class SmsStates:
    SELECT_RECIPIENT_TYPE = 10
    ENTER_PHONE_OR_GROUP   = 11
    SELECT_GROUP           = 12
    SELECT_TEMPLATE        = 13
    ENTER_CUSTOM_MESSAGE   = 14
    SELECT_ALPHA           = 15
    CONFIRM                = 16


# ------------------------------------------------------------------ #
#  Yordamchi funksiyalar
# ------------------------------------------------------------------ #

async def _is_admin(user_id: int) -> bool:
    return user_id in ADMINS


def _recipient_type_keyboard(user_data: dict) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(get_message(user_data, "sms_by_group")),
         KeyboardButton(get_message(user_data, "sms_by_phone"))],
        [KeyboardButton(get_message(user_data, "back_button"))],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def _back_keyboard(user_data: dict) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(get_message(user_data, "back_button"))]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# ------------------------------------------------------------------ #
#  Qadamlar
# ------------------------------------------------------------------ #

async def sms_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point — SMS menyu tugmasi bosilganda."""
    user_id = update.effective_user.id
    if not await _is_admin(user_id):
        await update.message.reply_text(
            get_message(context.user_data, "admin_not_authorized"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if not TEXTUP_EMAIL or not TEXTUP_PASSWORD:
        await update.message.reply_text(
            get_message(context.user_data, "sms_not_configured"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    context.user_data.pop("sms_data", None)

    await update.message.reply_text(
        get_message(context.user_data, "sms_select_recipient_type"),
        reply_markup=_recipient_type_keyboard(context.user_data),
    )
    return SmsStates.SELECT_RECIPIENT_TYPE


async def select_recipient_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guruh yoki telefon tanlash."""
    choice = update.message.text
    ud = context.user_data

    if choice == get_message(ud, "back_button"):
        await update.message.reply_text(
            get_message(ud, "sms_cancelled"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if choice == get_message(ud, "sms_by_group"):
        # TextUP guruhlarini yuklash
        await update.message.reply_text(get_message(ud, "sms_loading"), reply_markup=ReplyKeyboardRemove())
        try:
            client = get_textup_client()
            groups_data = await client.get_groups()
            groups = groups_data.get("groups", [])
        except (TextUpAuthError, TextUpAPIError) as e:
            logger.error("TextUP groups xatosi: %s", e)
            await update.message.reply_text(get_message(ud, "sms_api_error"))
            return ConversationHandler.END

        if not groups:
            await update.message.reply_text(get_message(ud, "sms_no_groups"))
            return ConversationHandler.END

        ud.setdefault("sms_data", {})["recipient_type"] = "group"
        ud["sms_data"]["available_groups"] = groups

        # Inline klaviatura bilan guruhlarni ko'rsatish
        buttons = [
            [InlineKeyboardButton(
                f"👥 {g['name']} ({g.get('status', '')})",
                callback_data=f"smsgrp_{g['id']}"
            )]
            for g in groups
        ]
        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            get_message(ud, "sms_select_group"),
            reply_markup=markup,
        )
        return SmsStates.SELECT_GROUP

    if choice == get_message(ud, "sms_by_phone"):
        ud.setdefault("sms_data", {})["recipient_type"] = "phone"
        await update.message.reply_text(
            get_message(ud, "sms_enter_phone"),
            reply_markup=_back_keyboard(ud),
        )
        return SmsStates.ENTER_PHONE_OR_GROUP

    # Noto'g'ri tanlov
    await update.message.reply_text(
        get_message(ud, "invalid_choice"),
        reply_markup=_recipient_type_keyboard(ud),
    )
    return SmsStates.SELECT_RECIPIENT_TYPE


async def group_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inline tugma orqali TextUP guruhi tanlanganda."""
    query = update.callback_query
    await query.answer()
    ud = context.user_data

    group_id = query.data.replace("smsgrp_", "")
    groups = ud.get("sms_data", {}).get("available_groups", [])
    selected = next((g for g in groups if g["id"] == group_id), None)
    if not selected:
        await query.edit_message_text(get_message(ud, "sms_api_error"))
        return ConversationHandler.END

    ud["sms_data"]["group_id"] = group_id
    ud["sms_data"]["group_name"] = selected["name"]

    await query.edit_message_text(
        get_message(ud, "sms_group_chosen", group_name=selected["name"])
    )
    return await _ask_template(query.message, context)


async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Telefon raqam qabul qilish."""
    text = update.message.text.strip()
    ud = context.user_data

    if text == get_message(ud, "back_button"):
        await update.message.reply_text(
            get_message(ud, "sms_select_recipient_type"),
            reply_markup=_recipient_type_keyboard(ud),
        )
        return SmsStates.SELECT_RECIPIENT_TYPE

    # Raqamlarni ajratib olish (+998901234567, 998901234567 yoki bo'sh joy bilan)
    raw_numbers = re.split(r"[,\n\s]+", text)
    phones = []
    for num in raw_numbers:
        num = num.strip()
        if not num:
            continue
        if not num.startswith("+"):
            num = "+" + num
        # Oddiy validatsiya (min 10 ta raqam)
        digits_only = re.sub(r"[^\d]", "", num)
        if len(digits_only) >= 10:
            phones.append(num)

    if not phones:
        await update.message.reply_text(
            get_message(ud, "sms_invalid_phone"),
            reply_markup=_back_keyboard(ud),
        )
        return SmsStates.ENTER_PHONE_OR_GROUP

    ud["sms_data"]["recipients"] = phones
    return await _ask_template(update.message, context)


async def _ask_template(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shablon tanlash yoki o'z matnini kiritish so'rash."""
    ud = context.user_data
    await message.reply_text(get_message(ud, "sms_loading"), reply_markup=ReplyKeyboardRemove())

    try:
        client = get_textup_client()
        tpl_data = await client.get_templates()
        templates = tpl_data.get("templates", [])
        # Faqat tasdiqlangan shablonlar (in_verify yoki active)
        active_tpl = [t for t in templates if t.get("status") in ("active", "approved", "in_verify")]
    except (TextUpAuthError, TextUpAPIError) as e:
        logger.error("TextUP templates xatosi: %s", e)
        active_tpl = []

    ud["sms_data"]["available_templates"] = active_tpl

    buttons = [
        [InlineKeyboardButton(f"📄 {t['name']}", callback_data=f"smstpl_{t['id']}")]
        for t in active_tpl
    ]
    # O'z matni tugmasi
    buttons.append([InlineKeyboardButton(
        get_message(ud, "sms_custom_message_button"), callback_data="smstpl_custom"
    )])

    markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        get_message(ud, "sms_select_template"),
        reply_markup=markup,
    )
    return SmsStates.SELECT_TEMPLATE


async def template_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shablon inline tugmasi bosilganda."""
    query = update.callback_query
    await query.answer()
    ud = context.user_data

    data = query.data.replace("smstpl_", "")

    if data == "custom":
        ud["sms_data"]["template_id"] = None
        await query.edit_message_text(get_message(ud, "sms_enter_custom_message"))
        # Matn kiritish uchun oddiy reply keyboard
        await query.message.reply_text(
            "✏️",
            reply_markup=_back_keyboard(ud),
        )
        return SmsStates.ENTER_CUSTOM_MESSAGE

    templates = ud.get("sms_data", {}).get("available_templates", [])
    selected = next((t for t in templates if t["id"] == data), None)
    if not selected:
        await query.edit_message_text(get_message(ud, "sms_api_error"))
        return ConversationHandler.END

    ud["sms_data"]["template_id"] = selected["id"]
    ud["sms_data"]["template_name"] = selected["name"]
    ud["sms_data"]["message"] = selected.get("content", "")

    await query.edit_message_text(
        get_message(ud, "sms_template_chosen", template_name=selected["name"])
    )
    return await _ask_alpha(query.message, context)


async def enter_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """O'z xabar matni kiritish."""
    text = update.message.text.strip()
    ud = context.user_data

    if text == get_message(ud, "back_button"):
        return await _ask_template(update.message, context)

    ud["sms_data"]["message"] = text
    ud["sms_data"]["template_id"] = None
    return await _ask_alpha(update.message, context)


async def _ask_alpha(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Alpha name (jo'natuvchi nomi) tanlash."""
    ud = context.user_data
    await message.reply_text(get_message(ud, "sms_loading"), reply_markup=ReplyKeyboardRemove())

    try:
        client = get_textup_client()
        alpha_data = await client.get_alpha_names()
        alphas = alpha_data.get("nickNames", alpha_data.get("data", []))
    except (TextUpAuthError, TextUpAPIError) as e:
        logger.warning("Alpha names yuklanmadi: %s", e)
        alphas = []

    ud["sms_data"]["available_alphas"] = alphas

    if not alphas:
        # Alpha yo'q — qisqa raqam bilan yuboriladi
        ud["sms_data"]["nickname_id"] = None
        return await _show_confirm(message, context)

    if len(alphas) == 1:
        # Faqat bitta alpha — avtomatik tanlash
        ud["sms_data"]["nickname_id"] = alphas[0].get("id")
        ud["sms_data"]["alpha_name"] = alphas[0].get("name", "")
        return await _show_confirm(message, context)

    # Bir nechtasi bo'lsa tanlash taklif qilamiz
    buttons = [
        [InlineKeyboardButton(
            f"📱 {a.get('name', a.get('id', ''))}",
            callback_data=f"smsalpha_{a.get('id', '')}"
        )]
        for a in alphas
    ]
    buttons.append([InlineKeyboardButton(
        get_message(ud, "sms_skip_alpha"), callback_data="smsalpha_skip"
    )])
    markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        get_message(ud, "sms_select_alpha"),
        reply_markup=markup,
    )
    return SmsStates.SELECT_ALPHA


async def alpha_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Alpha name inline tanlovi."""
    query = update.callback_query
    await query.answer()
    ud = context.user_data

    data = query.data.replace("smsalpha_", "")
    if data == "skip":
        ud["sms_data"]["nickname_id"] = None
        ud["sms_data"]["alpha_name"] = get_message(ud, "sms_short_number")
    else:
        alphas = ud.get("sms_data", {}).get("available_alphas", [])
        selected = next((a for a in alphas if str(a.get("id", "")) == data), None)
        ud["sms_data"]["nickname_id"] = selected.get("id") if selected else None
        ud["sms_data"]["alpha_name"] = selected.get("name", data) if selected else data

    await query.edit_message_text(
        get_message(ud, "sms_alpha_chosen", alpha_name=ud["sms_data"].get("alpha_name", ""))
    )
    return await _show_confirm(query.message, context)


async def _show_confirm(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Tasdiqlash xabarini ko'rsatish."""
    ud = context.user_data
    d = ud.get("sms_data", {})

    # Qabul qiluvchi
    if d.get("recipient_type") == "group":
        recipient_text = get_message(ud, "sms_confirm_group", group_name=d.get("group_name", ""))
    else:
        recipient_text = get_message(
            ud, "sms_confirm_phones",
            phones=", ".join(d.get("recipients", []))
        )

    # Shablon yoki matn
    if d.get("template_id"):
        content_text = get_message(ud, "sms_confirm_template", template_name=d.get("template_name", ""))
    else:
        msg = d.get("message", "")
        preview = msg[:80] + "..." if len(msg) > 80 else msg
        content_text = get_message(ud, "sms_confirm_message", message=preview)

    # Alpha name
    alpha_text = d.get("alpha_name") or get_message(ud, "sms_short_number")

    confirm_text = get_message(
        ud,
        "sms_confirm_text",
        recipient=recipient_text,
        content=content_text,
        alpha=alpha_text,
    )

    keyboard = [
        [KeyboardButton(get_message(ud, "sms_send_button"))],
        [KeyboardButton(get_message(ud, "sms_cancel_button"))],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await message.reply_text(confirm_text, reply_markup=markup, parse_mode="HTML")
    return SmsStates.CONFIRM


async def confirm_sms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Tasdiqlash yoki bekor qilish."""
    choice = update.message.text
    ud = context.user_data

    if choice == get_message(ud, "sms_cancel_button"):
        await update.message.reply_text(
            get_message(ud, "sms_cancelled"),
            reply_markup=ReplyKeyboardRemove(),
        )
        ud.pop("sms_data", None)
        return ConversationHandler.END

    if choice != get_message(ud, "sms_send_button"):
        await update.message.reply_text(get_message(ud, "invalid_choice"))
        return SmsStates.CONFIRM

    # SMS yuborish
    d = ud.get("sms_data", {})
    await update.message.reply_text(
        get_message(ud, "sms_sending"),
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        client = get_textup_client()
        sms_id = await client.send_sms(
            message=d.get("message") or None,
            template_id=d.get("template_id") or None,
            group_id=d.get("group_id") or None,
            recipients=d.get("recipients") or None,
            nickname_id=d.get("nickname_id") or None,
            name=f"TelegramBot_{update.effective_user.id}",
        )
        await update.message.reply_text(
            get_message(ud, "sms_sent_success", sms_id=sms_id)
        )
        logger.info(
            "SMS yuborildi. Foydalanuvchi: %s, smsId: %s",
            update.effective_user.id, sms_id
        )
    except (TextUpAuthError, TextUpAPIError) as e:
        logger.error("SMS yuborishda xato: %s", e)
        await update.message.reply_text(
            get_message(ud, "sms_sent_error", error=str(e))
        )

    ud.pop("sms_data", None)
    return ConversationHandler.END


# ------------------------------------------------------------------ #
#  ConversationHandler
# ------------------------------------------------------------------ #

def get_sms_conversation_handler() -> ConversationHandler:
    from keyboards import get_all_menu_buttons
    from language_handler import MESSAGES

    # SMS tugmasi pattern (barcha tillarda)
    sms_pattern = "|".join(
        [re.escape(MESSAGES[lang]["sms_button"]) for lang in MESSAGES]
    )

    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^({sms_pattern})$"), sms_start)
        ],
        states={
            SmsStates.SELECT_RECIPIENT_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_recipient_type)
            ],
            SmsStates.SELECT_GROUP: [
                CallbackQueryHandler(group_selected_callback, pattern=r"^smsgrp_")
            ],
            SmsStates.ENTER_PHONE_OR_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)
            ],
            SmsStates.SELECT_TEMPLATE: [
                CallbackQueryHandler(template_selected_callback, pattern=r"^smstpl_")
            ],
            SmsStates.ENTER_CUSTOM_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_custom_message)
            ],
            SmsStates.SELECT_ALPHA: [
                CallbackQueryHandler(alpha_selected_callback, pattern=r"^smsalpha_")
            ],
            SmsStates.CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_sms)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_message=False,
    )
