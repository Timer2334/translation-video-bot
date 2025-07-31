import sqlite3
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config.settings import ADMIN_IDS
from src.telegram_bot.db import (
    get_user,
    create_user,
    update_minutes_balance,
    update_video_balance,
    set_free_video,
    set_banned,
    DB_NAME,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from src.telegram_bot.admin_middleware import AdminOnlyMiddleware

from src.telegram_bot.texts import (
    ADMIN_MENU_WELCOME,
    BROADCAST_PROMPT,
    BROADCAST_FINISHED,
    GIVE_MINUTES_PROMPT_ID,
    GIVE_MINUTES_PROMPT_AMOUNT,
    GIVE_MINUTES_DONE,
    GIVE_VIDEOS_PROMPT_ID,
    GIVE_VIDEOS_PROMPT_AMOUNT,
    GIVE_VIDEOS_DONE,
    FREE_VIDEO_PROMPT_ID,
    FREE_VIDEO_DONE,
    BLOCK_PROMPT_ID,
    BLOCK_DONE,
    UNBLOCK_PROMPT_ID,
    UNBLOCK_DONE,
    COUNT_USERS_DONE,
    STATS_TODAY_SUCCESS,
    STATS_TODAY_NO_TABLE,
)

from src.telegram_bot.buttons import (
    BROADCAST_BUTTON,
    GIVE_MINUTES_BUTTON,
    GIVE_VIDEOS_BUTTON,
    FREE_VIDEO_BUTTON,
    BLOCK_BUTTON,
    UNBLOCK_BUTTON,
    COUNT_USERS_BUTTON,
    STATS_TODAY_BUTTON,
    ADMIN_MENU_BTN,
)

router_admin = Router(name="admin")
router_admin.message.middleware(AdminOnlyMiddleware())


class AdminMenuStates(StatesGroup):
    broadcast_waiting_message = State()
    give_minutes_waiting_user_id = State()
    give_minutes_waiting_amount = State()
    give_videos_waiting_user_id = State()
    give_videos_waiting_amount = State()
    set_free_video_waiting_user_id = State()
    block_waiting_user_id = State()
    unblock_waiting_user_id = State()


def get_admin_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text=BROADCAST_BUTTON, callback_data="admin_broadcast")],
        [
            InlineKeyboardButton(
                text=GIVE_MINUTES_BUTTON, callback_data="admin_give_minutes"
            ),
            InlineKeyboardButton(
                text=GIVE_VIDEOS_BUTTON, callback_data="admin_give_videos"
            ),
        ],
        [
            InlineKeyboardButton(
                text=FREE_VIDEO_BUTTON, callback_data="admin_free_video"
            )
        ],
        [
            InlineKeyboardButton(text=BLOCK_BUTTON, callback_data="admin_block_user"),
            InlineKeyboardButton(
                text=UNBLOCK_BUTTON, callback_data="admin_unblock_user"
            ),
        ],
        [
            InlineKeyboardButton(
                text=COUNT_USERS_BUTTON, callback_data="admin_count_users"
            )
        ],
        [
            InlineKeyboardButton(
                text=STATS_TODAY_BUTTON, callback_data="admin_stats_today"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def show_admin_menu_new_message(message: Message):
    await message.answer(ADMIN_MENU_WELCOME, reply_markup=get_admin_menu_kb())


@router_admin.message(F.text == ADMIN_MENU_BTN)
async def show_admin_menu_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await show_admin_menu_new_message(message)


@router_admin.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(BROADCAST_PROMPT)
    await state.set_state(AdminMenuStates.broadcast_waiting_message)
    await callback.answer()


@router_admin.message(StateFilter(AdminMenuStates.broadcast_waiting_message))
async def process_broadcast_message(message: Message, state: FSMContext):
    broadcast_msg = message
    await state.clear()
    delivered_count = 0
    removed_count = 0
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
    for (user_id,) in rows:
        try:
            await broadcast_msg.copy_to(user_id)
            delivered_count += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            with sqlite3.connect(DB_NAME) as conn2:
                c2 = conn2.cursor()
                c2.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                conn2.commit()
            removed_count += 1
        except Exception:
            pass
    msg_text = BROADCAST_FINISHED.format(
        delivered=delivered_count, removed=removed_count
    )
    await message.answer(msg_text)
    await show_admin_menu_new_message(message)


@router_admin.callback_query(F.data == "admin_give_minutes")
async def admin_give_minutes(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(GIVE_MINUTES_PROMPT_ID)
    await state.set_state(AdminMenuStates.give_minutes_waiting_user_id)
    await callback.answer()


@router_admin.message(StateFilter(AdminMenuStates.give_minutes_waiting_user_id))
async def admin_give_minutes_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Некорректный user_id. Введите число.")
        return
    await state.update_data(give_minutes_target=user_id)
    create_user(user_id)
    await message.answer(GIVE_MINUTES_PROMPT_AMOUNT)
    await state.set_state(AdminMenuStates.give_minutes_waiting_amount)


@router_admin.message(StateFilter(AdminMenuStates.give_minutes_waiting_amount))
async def admin_give_minutes_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Некорректное число. Введите положительное целое.")
        return
    data = await state.get_data()
    user_id = data.get("give_minutes_target")
    await state.clear()
    if user_id is None:
        await message.answer("Ошибка: не найден user_id. Попробуйте заново.")
        return
    row = get_user(user_id)
    if not row:
        create_user(user_id)
        row = get_user(user_id)
    current_minutes = row[2]
    new_balance = current_minutes + amount
    update_minutes_balance(user_id, new_balance)
    done_text = GIVE_MINUTES_DONE.format(user_id=user_id, new_balance=new_balance)
    await message.answer(done_text)
    await show_admin_menu_new_message(message)


@router_admin.callback_query(F.data == "admin_give_videos")
async def admin_give_videos(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(GIVE_VIDEOS_PROMPT_ID)
    await state.set_state(AdminMenuStates.give_videos_waiting_user_id)
    await callback.answer()


@router_admin.message(StateFilter(AdminMenuStates.give_videos_waiting_user_id))
async def admin_give_videos_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Некорректный user_id. Введите число.")
        return
    await state.update_data(give_videos_target=user_id)
    create_user(user_id)
    await message.answer(GIVE_VIDEOS_PROMPT_AMOUNT)
    await state.set_state(AdminMenuStates.give_videos_waiting_amount)


@router_admin.message(StateFilter(AdminMenuStates.give_videos_waiting_amount))
async def admin_give_videos_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Некорректное число. Введите положительное целое.")
        return
    data = await state.get_data()
    user_id = data.get("give_videos_target")
    await state.clear()
    if user_id is None:
        await message.answer("Ошибка: не найден user_id. Попробуйте заново.")
        return
    row = get_user(user_id)
    if not row:
        create_user(user_id)
        row = get_user(user_id)
    current_video = row[4]
    new_balance = current_video + amount
    update_video_balance(user_id, new_balance)
    done_text = GIVE_VIDEOS_DONE.format(user_id=user_id, new_balance=new_balance)
    await message.answer(done_text)
    await show_admin_menu_new_message(message)


@router_admin.callback_query(F.data == "admin_free_video")
async def admin_free_video(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(FREE_VIDEO_PROMPT_ID)
    await state.set_state(AdminMenuStates.set_free_video_waiting_user_id)
    await callback.answer()


@router_admin.message(StateFilter(AdminMenuStates.set_free_video_waiting_user_id))
async def admin_set_free_video_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Некорректный user_id.")
        return
    await state.clear()
    create_user(user_id)
    row = get_user(user_id)
    if not row:
        await message.answer("Не удалось создать/получить пользователя.")
        return
    old_val = row[3]
    new_val = 0 if old_val == 1 else 1
    set_free_video(user_id, new_val)
    done_text = FREE_VIDEO_DONE.format(
        user_id=user_id, old_val=old_val, new_val=new_val
    )
    await message.answer(done_text)
    await show_admin_menu_new_message(message)


@router_admin.callback_query(F.data == "admin_block_user")
async def admin_block_user(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(BLOCK_PROMPT_ID)
    await state.set_state(AdminMenuStates.block_waiting_user_id)
    await callback.answer()


@router_admin.message(StateFilter(AdminMenuStates.block_waiting_user_id))
async def process_block_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Некорректный user_id.")
        return
    await state.clear()
    create_user(user_id)
    try:
        await message.bot.send_message(
            user_id, "Вы были заблокированы администратором."
        )
    except:
        pass
    set_banned(user_id, 1)
    done_text = BLOCK_DONE.format(user_id=user_id)
    await message.answer(done_text)
    await show_admin_menu_new_message(message)


@router_admin.callback_query(F.data == "admin_unblock_user")
async def admin_unblock_user(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(UNBLOCK_PROMPT_ID)
    await state.set_state(AdminMenuStates.unblock_waiting_user_id)
    await callback.answer()


@router_admin.message(StateFilter(AdminMenuStates.unblock_waiting_user_id))
async def process_unblock_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Некорректный user_id.")
        return
    await state.clear()
    create_user(user_id)
    set_banned(user_id, 0)
    try:
        await message.bot.send_message(user_id, "Вы разблокированы администратором.")
    except:
        pass
    done_text = UNBLOCK_DONE.format(user_id=user_id)
    await message.answer(done_text)
    await show_admin_menu_new_message(message)


@router_admin.callback_query(F.data == "admin_count_users")
async def admin_count_users(callback: CallbackQuery):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
    msg_text = COUNT_USERS_DONE.format(count=count)
    await callback.message.answer(msg_text)
    await show_admin_menu_new_message(callback.message)
    await callback.answer()


@router_admin.callback_query(F.data == "admin_stats_today")
async def admin_stats_today_callback(callback: CallbackQuery):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT IFNULL(SUM(amount), 0), IFNULL(SUM(price), 0)
                FROM purchase_logs
                WHERE purchase_type='minutes'
                AND DATE(created_at) = DATE('now')
                """
            )
            row = cursor.fetchone()
            total_minutes = row[0]
            total_rub = row[1]
            msg_text = STATS_TODAY_SUCCESS.format(
                total_minutes=total_minutes, total_rub=total_rub
            )
        except sqlite3.OperationalError:
            msg_text = STATS_TODAY_NO_TABLE
    await callback.message.answer(msg_text)
    await show_admin_menu_new_message(callback.message)
    await callback.answer()
