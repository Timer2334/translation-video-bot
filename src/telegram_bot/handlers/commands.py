from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from src.telegram_bot.db import create_user, get_user
from src.telegram_bot.texts import (
    TEXT_START,
    TEXT_SUPPORT,
    TEXT_ABOUT,
    TEXT_PARTNERS,
    TEXT_ACCOUNT_TEMPLATE,
)
from src.telegram_bot.buttons import (
    SEND_VIDEO_BTN,
    MY_ACCOUNT_BTN,
    SUPPORT_BTN,
    ABOUT_BTN,
    PARTNERS_BTN,
    ADMIN_MENU_BTN,
)
from config.settings import ADMIN_IDS
from src.telegram_bot.user_state import user_db

router_commands = Router()

# ------------------------------------------------------------------
# Reply‑клавиатура главного меню
# ------------------------------------------------------------------
def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text=SEND_VIDEO_BTN)],
        [KeyboardButton(text=MY_ACCOUNT_BTN), KeyboardButton(text=SUPPORT_BTN)],
        [KeyboardButton(text=ABOUT_BTN), KeyboardButton(text=PARTNERS_BTN)],
    ]
    if user_id in ADMIN_IDS:
        kb.append([KeyboardButton(text=ADMIN_MENU_BTN)])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ------------------------------------------------------------------
# /start
# ------------------------------------------------------------------
@router_commands.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # создаём пользователя в БД, если нужно
    create_user(user_id)

    # инициализируем in‑memory хранилище
    data = user_db.setdefault(user_id, {})
    data.setdefault("source_lang", "en")
    data.setdefault("target_lang", "ru")

    await message.answer(TEXT_START, reply_markup=get_main_menu(user_id))


# ------------------------------------------------------------------
# Статические разделы: поддержка / о боте / партнёры
# ------------------------------------------------------------------
@router_commands.message(F.text == SUPPORT_BTN)
async def support_handler(message: Message):
    await message.answer(TEXT_SUPPORT, reply_markup=get_main_menu(message.from_user.id))


@router_commands.message(F.text == ABOUT_BTN)
async def about_handler(message: Message):
    await message.answer(TEXT_ABOUT, reply_markup=get_main_menu(message.from_user.id))


@router_commands.message(F.text == PARTNERS_BTN)
async def partners_handler(message: Message):
    await message.answer(TEXT_PARTNERS, reply_markup=get_main_menu(message.from_user.id))


# ------------------------------------------------------------------
# «👤 Мой аккаунт»
# ------------------------------------------------------------------
@router_commands.message(F.text == MY_ACCOUNT_BTN)
async def my_account_handler(message: Message):
    user_id = message.from_user.id
    row = get_user(user_id)
    if row is None:
        create_user(user_id)
        row = get_user(user_id)

    _, _, minutes_balance, free_video, video_balance, banned = row
    free_str = "не использован" if free_video == 1 else "использован"
    ban_str = "Да" if banned else "Нет"

    txt = TEXT_ACCOUNT_TEMPLATE.format(
        free=free_str,
        minutes=minutes_balance,
        videos=video_balance,
        ban=ban_str,
    )
    await message.answer(txt, reply_markup=get_main_menu(user_id), parse_mode="HTML")
