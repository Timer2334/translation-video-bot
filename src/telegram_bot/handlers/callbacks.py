from aiogram import Router, F
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from src.telegram_bot.db import create_user, get_user
from src.telegram_bot.texts import (
    TEXT_SEND_VIDEO,
    TEXT_CHOOSE_MINUTES,
    TEXT_CHOOSE_VIDEOS,
    TEXT_CUSTOM_NOT_SUPPORTED,
    TEXT_BUY_MINUTE_RESULT,
    TEXT_BUY_VIDEO_RESULT,
    TEXT_ACCOUNT_TEMPLATE,
)
from src.telegram_bot.buttons import (
    SEND_VIDEO_BTN,
    MINUTE_1_BTN,
    MINUTE_5_BTN,
    MINUTE_30_BTN,
    MINUTE_60_BTN,
    MINUTE_CUSTOM_BTN,
    VIDEO_1_BTN,
    VIDEO_5_BTN,
    VIDEO_10_BTN,
    VIDEO_20_BTN,
    VIDEO_CUSTOM_BTN,
    BTN_BACK_TO_ACCOUNT,
    BTN_PAY_METHOD,
)
from src.utils.languages import SOURCE_LANGS, TARGET_LANGS
from src.telegram_bot.user_state import user_db

router_callbacks = Router()

# ---------------------------------------------------------------------------
# ������ ������� ������������ ���� ������
# ---------------------------------------------------------------------------

def _build_source_kb() -> InlineKeyboardMarkup:
    """Keyboard with source‑language options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=val, callback_data=f"choose_source:{key}")]
            for key, val in SOURCE_LANGS.items()
        ]
    )


def _build_target_kb() -> InlineKeyboardMarkup:
    """Keyboard with target‑language options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=val, callback_data=f"choose_target:{key}")]
            for key, val in TARGET_LANGS.items()
        ]
    )


# ---------------------------------------------------------------------------
# Шаг 0. Пользователь нажал «🎬 Перевести видео»
# ---------------------------------------------------------------------------

@router_callbacks.message(F.text == SEND_VIDEO_BTN)
async def handle_send_video(message: Message):
    """Entry‑point when user taps the main‑menu button.

    • If languages are already stored, ask for confirmation.
    • Otherwise, start normal language selection.
    """
    user_id = message.from_user.id
    data = user_db.get(user_id, {})
    s_lang = data.get("source_lang")
    t_lang = data.get("target_lang")

    # The user has picked languages before → ask to confirm or change
    if s_lang and t_lang:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data="langs_confirm"),
                    InlineKeyboardButton(text="🔄 Изменить языки", callback_data="langs_change"),
                ]
            ]
        )
        await message.answer(
            f"Хотите ли вы перевести с <b>{SOURCE_LANGS[s_lang]}</b> на <b>{TARGET_LANGS[t_lang]}</b>?",
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        # First time – start the normal flow
        await message.answer("Выберите исходный язык:", reply_markup=_build_source_kb())


# ---------------------------------------------------------------------------
# Кнопки подтверждения / изменения языков
# ---------------------------------------------------------------------------

@router_callbacks.callback_query(F.data == "langs_confirm")
async def confirm_langs(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_db.get(user_id, {})
    s_lang = data.get("source_lang")
    t_lang = data.get("target_lang")
    await callback.message.edit_reply_markup(None)  # убираем кнопки
    await callback.message.answer(
        f"Отлично! Вы выбрали перевод с {SOURCE_LANGS[s_lang]} на {TARGET_LANGS[t_lang]}.\n{TEXT_SEND_VIDEO}"
    )
    await callback.answer()


@router_callbacks.callback_query(F.data == "langs_change")
async def change_langs(callback: CallbackQuery):
    # Удаляем сообщение с кнопками и запускаем выбор заново
    await callback.answer()
    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer("Выберите исходный язык:", reply_markup=_build_source_kb())


# ---------------------------------------------------------------------------
# Шаг 1. Выбор исходного языка
# ---------------------------------------------------------------------------

@router_callbacks.callback_query(F.data.startswith("choose_source:"))
async def choose_source_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    chosen_source = callback.data.split(":")[1]
    data = user_db.setdefault(user_id, {})
    data["source_lang"] = chosen_source

    # Переходим к выбору целевого языка
    await callback.answer()
    await callback.message.answer("Выберите язык перевода:", reply_markup=_build_target_kb())

    # Удаляем сообщение с исходными языками
    try:
        await callback.message.delete()
    except:
        pass


# ---------------------------------------------------------------------------
# Шаг 2. Выбор целевого языка
# ---------------------------------------------------------------------------

@router_callbacks.callback_query(F.data.startswith("choose_target:"))
async def choose_target_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    chosen_target = callback.data.split(":")[1]
    data = user_db.setdefault(user_id, {})
    data["target_lang"] = chosen_target

    await callback.answer()
    s_lang = data["source_lang"]
    t_lang = data["target_lang"]

    await callback.message.answer(
        f"Отлично! Вы выбрали перевод с {SOURCE_LANGS[s_lang]} на {TARGET_LANGS[t_lang]}.\n{TEXT_SEND_VIDEO}"
    )

    # Удаляем сообщение с целевыми языками
    try:
        await callback.message.delete()
    except:
        pass


# ---------------------------------------------------------------------------
# === Далее идёт существующий код покупки минут / видео и прочего ===
# ---------------------------------------------------------------------------
# (оставлен без изменений, кроме перемещения ниже новых обработчиков)

@router_callbacks.callback_query(F.data == "buy_minutes")
async def buy_minutes_callback(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=MINUTE_1_BTN, callback_data="buy_minutes_select:1"),
                InlineKeyboardButton(text=MINUTE_5_BTN, callback_data="buy_minutes_select:5"),
            ],
            [
                InlineKeyboardButton(text=MINUTE_30_BTN, callback_data="buy_minutes_select:30"),
                InlineKeyboardButton(text=MINUTE_60_BTN, callback_data="buy_minutes_select:60"),
            ],
            [
                InlineKeyboardButton(text=MINUTE_CUSTOM_BTN, callback_data="buy_minutes_select:custom"),
                InlineKeyboardButton(text=BTN_BACK_TO_ACCOUNT, callback_data="back_to_account"),
            ],
        ]
    )
    await callback.message.edit_text(TEXT_CHOOSE_MINUTES, reply_markup=kb)
    await callback.answer()


@router_callbacks.callback_query(F.data.startswith("buy_minutes_select:"))
async def buy_minutes_select_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    chosen_data = callback.data.split(":")[1]
    if chosen_data == "custom":
        await callback.answer(TEXT_CUSTOM_NOT_SUPPORTED, show_alert=True)
        return
    count = int(chosen_data)
    price = float(count)
    data = user_db.setdefault(user_id, {})
    data.update(
        {
            "pending_purchase_type": "minutes",
            "pending_purchase_count": count,
            "pending_purchase_price": price,
        }
    )
    text_msg = TEXT_BUY_MINUTE_RESULT.format(count=count, price=price)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_PAY_METHOD, callback_data="payment_choose_method")],
            [InlineKeyboardButton(text=BTN_BACK_TO_ACCOUNT, callback_data="buy_minutes")],
        ]
    )
    await callback.message.edit_text(text_msg, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router_callbacks.callback_query(F.data == "buy_videos")
async def buy_videos_callback(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=VIDEO_1_BTN, callback_data="buy_videos_select:1"),
                InlineKeyboardButton(text=VIDEO_5_BTN, callback_data="buy_videos_select:5"),
            ],
            [
                InlineKeyboardButton(text=VIDEO_10_BTN, callback_data="buy_videos_select:10"),
                InlineKeyboardButton(text=VIDEO_20_BTN, callback_data="buy_videos_select:20"),
            ],
            [
                InlineKeyboardButton(text=VIDEO_CUSTOM_BTN, callback_data="buy_videos_select:custom"),
                InlineKeyboardButton(text=BTN_BACK_TO_ACCOUNT, callback_data="back_to_account"),
            ],
        ]
    )
    await callback.message.edit_text(TEXT_CHOOSE_VIDEOS, reply_markup=kb)
    await callback.answer()


@router_callbacks.callback_query(F.data.startswith("buy_videos_select:"))
async def buy_videos_select_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    chosen_data = callback.data.split(":")[1]
    if chosen_data == "custom":
        await callback.answer(TEXT_CUSTOM_NOT_SUPPORTED, show_alert=True)
        return
    count = int(chosen_data)
    price = float(count * 5)
    data = user_db.setdefault(user_id, {})
    data.update(
        {
            "pending_purchase_type": "videos",
            "pending_purchase_count": count,
            "pending_purchase_price": price,
        }
    )
    text_msg = TEXT_BUY_VIDEO_RESULT.format(count=count, price=price)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_PAY_METHOD, callback_data="payment_choose_method")],
            [InlineKeyboardButton(text=BTN_BACK_TO_ACCOUNT, callback_data="buy_videos")],
        ]
    )
    await callback.message.edit_text(text_msg, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router_callbacks.callback_query(F.data == "back_to_account")
async def back_to_account_callback(callback: CallbackQuery):
    # импорт здесь во избежание циклической зависимости
    from .commands import get_main_menu

    await callback.answer()
    user_id = callback.from_user.id
    row = get_user(user_id)
    if row is None:
        create_user(user_id)
        row = get_user(user_id)
    _, _, minutes_balance, free_video, video_balance, banned = row
    free_str = "не использован" if free_video == 1 else "использован"
    ban_str = "Да" if banned else "Нет"
    txt = TEXT_ACCOUNT_TEMPLATE.format(
        free=free_str, minutes=minutes_balance, videos=video_balance, ban=ban_str
    )
    await callback.message.edit_text(txt, reply_markup=get_main_menu(user_id), parse_mode="HTML")
