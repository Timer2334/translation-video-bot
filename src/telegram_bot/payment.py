import math
import time
import asyncio
import logging
import aiohttp
import random
import string
import sqlite3

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    PreCheckoutQuery,
    Message,
    ContentType,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from src.telegram_bot.db import (
    get_user,
    create_user,
    update_minutes_balance,
    update_video_balance,
    DB_NAME,
)

from aiocryptopay import AioCryptoPay, Networks

CRYPTOBOT_API_TOKEN = "105812:AAw8nbwwIOjrHfcp3BiZLgsDsUInQCZAxQZ"
cryptobot_api = AioCryptoPay(
    token=CRYPTOBOT_API_TOKEN,
    network=Networks.MAIN_NET,
)

CRYPTOBOT_CURRENCY_SLUG = {
    "USDT": "tether",
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "BUSD": "binance-usd",
    "USDC": "usd-coin",
    "TON": "the-open-network",
    "TRX": "tron",
    "LTC": "litecoin",
}

MAIN_CURRENCIES = ["USDT", "ETH", "TON", "LTC", "BTC", "TRX"]
OTHER_CURRENCIES = ["BNB", "BUSD", "USDC"]

TELEGRAM_STARS_TOKEN = ""
STARS_PER_RUB = 0.5  # 1 звезда = 2 руб => 1 руб = 0.5 звезды

ADMIN_IDS = [622328140, 987654321]

# Хранение инвойсов для CryptoBot
user_crypto_invoices = {}

# Хранилище ручных оплат
pending_manual_payments = {}

router_payment = Router()


class ManualPayStates(StatesGroup):
    WAIT_FOR_RECEIPT = State()


from src.telegram_bot.texts import (
    TEXT_CHOOSE_PAYMENT_METHOD,
    TEXT_PAY_CARD,
    TEXT_SEND_RECEIPT,
    TEXT_RECEIPT_ARRIVED,
    TEXT_CHECK_USER,
    TEXT_PAYMENT_CONFIRMED,
    TEXT_PAYMENT_REJECTED,
    TEXT_INVOICE_CREATING,
    TEXT_INVOICE_ERROR,
    TEXT_INVOICE_DONE,
    TEXT_CRYPTO_PROMPT,
    TEXT_CRYPTO_OTHER,
    TEXT_PAYMENT_SUCCESS,
    TEXT_PAYMENT_PROCESSED,
    TEXT_MANUAL_CONFIRMED_MSG,
    TEXT_MANUAL_REJECTED_MSG,
)

from src.telegram_bot.buttons import (
    PAY_CARD_BTN,
    PAY_CRYPTO_BTN,
    PAY_STARS_BTN,
    BTN_BACK_TO_ACCOUNT,
    BTN_USER_PAID,
    BTN_CONFIRM,
    BTN_REJECT,
    BTN_PAY_NOW,
    BTN_OTHER_CURRENCIES,
)


def setup_payment_routes(user_db: dict):
    """
    Регистрируем callback-хендлеры.
    """

    @router_payment.callback_query(F.data == "payment_choose_method")
    async def payment_choose_method_callback(callback: CallbackQuery):
        """
        Выбор способа оплаты: карта, крипто, Stars
        """
        user_id = callback.from_user.id
        data = user_db[user_id]
        ptype = data.get("pending_purchase_type", "minutes")
        count = data.get("pending_purchase_count", 1)
        price = data.get("pending_purchase_price", 50.0)

        text_msg = TEXT_CHOOSE_PAYMENT_METHOD.format(
            count=count, ptype=ptype, price=price
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=PAY_CARD_BTN, callback_data="payment_card")],
                [
                    InlineKeyboardButton(
                        text=PAY_CRYPTO_BTN, callback_data="payment_crypto"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=PAY_STARS_BTN, callback_data="payment_stars"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BTN_BACK_TO_ACCOUNT, callback_data="back_to_account"
                    )
                ],
            ]
        )
        await callback.message.edit_text(text_msg, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    # ============== ОПЛАТА ПО КАРТЕ/СБП ==================
    @router_payment.callback_query(F.data == "payment_card")
    async def payment_card_callback(callback: CallbackQuery):
        user_id = callback.from_user.id
        data = user_db[user_id]
        price = data.get("pending_purchase_price", 50.0)

        text_msg = TEXT_PAY_CARD.format(price=price)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=BTN_USER_PAID, callback_data="user_paid_receipt"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BTN_BACK_TO_ACCOUNT, callback_data="payment_choose_method"
                    )
                ],
            ]
        )
        await callback.message.edit_text(text_msg, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @router_payment.callback_query(F.data == "user_paid_receipt")
    async def user_paid_receipt_callback(callback: CallbackQuery, state: FSMContext):
        """
        «Я оплатил» -> ждём PDF или фото чека
        """
        await callback.answer()
        await state.set_state(ManualPayStates.WAIT_FOR_RECEIPT)
        await callback.message.answer(TEXT_SEND_RECEIPT)

    @router_payment.message(
        StateFilter(ManualPayStates.WAIT_FOR_RECEIPT),
        F.content_type.in_({ContentType.DOCUMENT, ContentType.PHOTO}),
    )
    async def handle_user_receipt(message: Message, state: FSMContext):
        user_id = message.from_user.id
        data = user_db.get(user_id, {})
        ptype = data.get("pending_purchase_type", "minutes")
        count = data.get("pending_purchase_count", 1)

        pending_id = generate_pending_id()
        pending_manual_payments[pending_id] = {
            "user_id": user_id,
            "purchase_type": ptype,
            "purchase_count": count,
            "messages": [],
            "status": "pending",
        }

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=BTN_CONFIRM, callback_data=f"manual_confirm:{pending_id}"
                    ),
                    InlineKeyboardButton(
                        text=BTN_REJECT, callback_data=f"manual_reject:{pending_id}"
                    ),
                ]
            ]
        )

        forward_text = TEXT_CHECK_USER.format(user_id=user_id, count=count, ptype=ptype)

        # Пересылаем чек всем админам
        for admin_id in ADMIN_IDS:
            try:
                if message.photo:
                    photo = message.photo[-1].file_id
                    sent = await message.bot.send_photo(
                        admin_id,
                        photo,
                        caption=forward_text,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                elif message.document:
                    doc = message.document.file_id
                    sent = await message.bot.send_document(
                        admin_id,
                        doc,
                        caption=forward_text,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                else:
                    sent = await message.bot.send_message(
                        admin_id, forward_text, parse_mode="HTML", reply_markup=kb
                    )

                pending_manual_payments[pending_id]["messages"].append(
                    (admin_id, sent.message_id)
                )
            except:
                pass

        await state.clear()
        await message.answer(TEXT_RECEIPT_ARRIVED)

    # Админ подтверждает оплату
    @router_payment.callback_query(F.data.startswith("manual_confirm:"))
    async def manual_confirm_payment(callback: CallbackQuery):
        pending_id = callback.data.split(":")[1]
        info = pending_manual_payments.get(pending_id)
        if not info or info["status"] != "pending":
            await callback.answer(TEXT_PAYMENT_PROCESSED, show_alert=True)
            return

        info["status"] = "confirmed"
        user_id = info["user_id"]
        ptype = info["purchase_type"]
        count = info["purchase_count"]

        data = user_db.setdefault(user_id, {})
        price = data.get("pending_purchase_price", 0.0)

        row = get_user(user_id)
        if row is None:
            create_user(user_id)
            row = get_user(user_id)

        if ptype == "minutes":
            current_minutes = row[2]
            new_minutes = current_minutes + count
            update_minutes_balance(user_id, new_minutes)
            data["minute_balance"] = data.get("minute_balance", 0) + count
        else:
            current_videos = row[4]
            new_videos = current_videos + count
            update_video_balance(user_id, new_videos)
            data["video_balance"] = data.get("video_balance", 0) + count

        log_purchase(user_id, ptype, count, price)

        try:
            await callback.message.bot.send_message(
                user_id,
                TEXT_PAYMENT_CONFIRMED.format(count=count, ptype=ptype),
            )
        except:
            pass

        remove_inline_buttons(info["messages"], callback.message.bot, "Подтвержден ✅")

        await callback.answer("Платёж подтверждён!")
        await callback.message.edit_caption(
            caption=TEXT_MANUAL_CONFIRMED_MSG, reply_markup=None
        )

    # Админ отклоняет оплату
    @router_payment.callback_query(F.data.startswith("manual_reject:"))
    async def manual_reject_payment(callback: CallbackQuery):
        pending_id = callback.data.split(":")[1]
        info = pending_manual_payments.get(pending_id)
        if not info or info["status"] != "pending":
            await callback.answer(TEXT_PAYMENT_PROCESSED, show_alert=True)
            return

        info["status"] = "rejected"
        user_id = info["user_id"]
        ptype = info["purchase_type"]
        count = info["purchase_count"]

        try:
            await callback.message.bot.send_message(
                user_id,
                TEXT_PAYMENT_REJECTED.format(count=count, ptype=ptype),
            )
        except:
            pass

        remove_inline_buttons(info["messages"], callback.message.bot, "Отклонен ❌")
        await callback.answer("Отклонено!")
        await callback.message.edit_caption(
            caption=TEXT_MANUAL_REJECTED_MSG, reply_markup=None
        )

    # ============ ОПЛАТА ЧЕРЕЗ CRYPTOBOT ============
    @router_payment.callback_query(F.data == "payment_crypto")
    async def payment_crypto_callback(callback: CallbackQuery):
        kb_rows = []
        row_buf = []
        for i, cur in enumerate(MAIN_CURRENCIES):
            row_buf.append(
                InlineKeyboardButton(text=cur, callback_data=f"cryptobot_select:{cur}")
            )
            if (i + 1) % 2 == 0:
                kb_rows.append(row_buf)
                row_buf = []
        if row_buf:
            kb_rows.append(row_buf)
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=BTN_OTHER_CURRENCIES, callback_data="cryptobot_other_menu"
                )
            ]
        )
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=BTN_BACK_TO_ACCOUNT, callback_data="payment_choose_method"
                )
            ]
        )

        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await callback.message.edit_text(TEXT_CRYPTO_PROMPT, reply_markup=kb)
        await callback.answer()

    @router_payment.callback_query(F.data == "cryptobot_other_menu")
    async def cryptobot_other_menu(callback: CallbackQuery):
        kb_rows = []
        row_buf = []
        for i, cur in enumerate(OTHER_CURRENCIES):
            row_buf.append(
                InlineKeyboardButton(text=cur, callback_data=f"cryptobot_select:{cur}")
            )
            if (i + 1) % 2 == 0:
                kb_rows.append(row_buf)
                row_buf = []
        if row_buf:
            kb_rows.append(row_buf)
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=BTN_BACK_TO_ACCOUNT, callback_data="payment_crypto"
                )
            ]
        )

        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await callback.message.edit_text(TEXT_CRYPTO_OTHER, reply_markup=kb)
        await callback.answer()

    @router_payment.callback_query(F.data.startswith("cryptobot_select:"))
    async def cryptobot_select_callback(callback: CallbackQuery):
        user_id = callback.from_user.id
        data = user_db[user_id]
        ptype = data.get("pending_purchase_type", "minutes")
        count = data.get("pending_purchase_count", 1)
        price = data.get("pending_purchase_price", 50.0)

        currency = callback.data.split(":")[1]

        await callback.message.edit_text(TEXT_INVOICE_CREATING)

        try:
            slug = CRYPTOBOT_CURRENCY_SLUG.get(currency, None)
            if not slug:
                raise Exception(f"Нет slug для {currency}")

            crypto_amount = await convert_rub_to_crypto(slug, price)
            invoice = await cryptobot_api.create_invoice(
                asset=currency,
                amount=crypto_amount,
                description=f"Покупка {count} {ptype}",
            )
            invoice_id = invoice.invoice_id
            pay_url = invoice.bot_invoice_url

            user_crypto_invoices[user_id] = {
                "invoice_id": invoice_id,
                "purchase_type": ptype,
                "purchase_count": count,
                "purchase_price": price,
                "created_at": time.time(),
            }

            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=BTN_PAY_NOW, url=pay_url)],
                    [
                        InlineKeyboardButton(
                            text=BTN_BACK_TO_ACCOUNT, callback_data="payment_crypto"
                        )
                    ],
                ]
            )
            done_text = TEXT_INVOICE_DONE.format(price=price, count=count, ptype=ptype)
            await callback.message.edit_text(
                done_text, parse_mode="HTML", reply_markup=kb
            )

        except Exception as e:
            await callback.message.edit_text(TEXT_INVOICE_ERROR.format(error=str(e)))
        await callback.answer()

    # ============ ОПЛАТА ЧЕРЕЗ TELEGRAM STARS ============
    @router_payment.callback_query(F.data == "payment_stars")
    async def payment_stars_callback(callback: CallbackQuery):
        user_id = callback.from_user.id
        data = user_db[user_id]
        ptype = data.get("pending_purchase_type", "minutes")
        count = data.get("pending_purchase_count", 1)
        price = data.get("pending_purchase_price", 50.0)

        stars_needed = math.ceil(price * STARS_PER_RUB)

        text_msg = (
            f"Оплата <b>{count} {ptype}</b> через Telegram Stars\n"
            f"~ {stars_needed} ⭐\n"
            f"Сумма: {price} руб."
        )
        await callback.message.edit_text(text_msg, parse_mode="HTML")

        prices = [LabeledPrice(label="Stars", amount=stars_needed)]
        await callback.message.answer_invoice(
            title="Покупка минут/видео",
            description=f"{count} {ptype}",
            provider_token=TELEGRAM_STARS_TOKEN,
            currency="XTR",
            prices=prices,
            payload="stars_purchase",
        )
        await callback.answer()

    @router_payment.pre_checkout_query()
    async def pre_checkout_query_handler(pre_checkout_q: PreCheckoutQuery):
        await pre_checkout_q.answer(ok=True)

    @router_payment.message(F.successful_payment)
    async def success_payment_handler(message: Message):
        user_id = message.from_user.id
        data = user_db[user_id]

        ptype = data.pop("pending_purchase_type", "minutes")
        count = data.pop("pending_purchase_count", 1)
        price = data.pop("pending_purchase_price", 0.0)

        row = get_user(user_id)
        if row is None:
            create_user(user_id)
            row = get_user(user_id)

        if ptype == "minutes":
            current_minutes = row[2]
            new_minutes = current_minutes + count
            update_minutes_balance(user_id, new_minutes)
            data["minute_balance"] = new_minutes
        else:
            current_videos = row[4]
            new_videos = current_videos + count
            update_video_balance(user_id, new_videos)
            data["video_balance"] = new_videos

        log_purchase(user_id, ptype, count, price)

        await message.answer(TEXT_PAYMENT_SUCCESS.format(count=count, ptype=ptype))


# -----------------------------------------------------------------
#  проверка CryptoBot
# -----------------------------------------------------------------
async def start_crypto_invoices_task(bot, user_db):
    logging.info("[payment] Запуск мониторинга CryptoBot-инвойсов...")
    asyncio.create_task(check_crypto_invoices(bot, user_db))


async def check_crypto_invoices(bot, user_db):
    while True:
        await asyncio.sleep(10)
        for uid, invoice_info in list(user_crypto_invoices.items()):
            invoice_id = invoice_info["invoice_id"]
            ptype = invoice_info["purchase_type"]
            count = invoice_info["purchase_count"]
            price = invoice_info.get("purchase_price", 0.0)

            try:
                inv_obj = await cryptobot_api.get_invoices(invoice_ids=invoice_id)
                if inv_obj and inv_obj.status == "paid":
                    user_crypto_invoices.pop(uid, None)

                    data = user_db.setdefault(uid, {})
                    row = get_user(uid)
                    if row is None:
                        create_user(uid)
                        row = get_user(uid)

                    if ptype == "minutes":
                        current_minutes = row[2]
                        new_minutes = current_minutes + count
                        update_minutes_balance(uid, new_minutes)
                        data["minute_balance"] = data.get("minute_balance", 0) + count
                    else:
                        current_videos = row[4]
                        new_videos = current_videos + count
                        update_video_balance(uid, new_videos)
                        data["video_balance"] = data.get("video_balance", 0) + count

                    log_purchase(uid, ptype, count, price)

                    try:
                        await bot.send_message(
                            uid,
                            f"✅ Оплата получена. Начислено {count} {ptype}.",
                        )
                    except:
                        pass

            except Exception as e:
                logging.error(
                    f"[payment] check_crypto_invoices: invoice_id={invoice_id}, ошибка: {e}"
                )


# -----------------------------------------------------------------
# -----------------------------------------------------------------
async def convert_rub_to_crypto(crypto_slug: str, rub_amount: float) -> float:
    rate = await get_exchange_rate(crypto_slug)
    return round(rub_amount / rate, 8)


async def get_exchange_rate(crypto_slug: str) -> float:
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_slug}&vs_currencies=rub"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(1)
                        continue
                    data = await resp.json()
                    if crypto_slug in data and "rub" in data[crypto_slug]:
                        return float(data[crypto_slug]["rub"])
        except (aiohttp.ClientError, asyncio.TimeoutError):
            await asyncio.sleep(1)

    raise Exception(f"Не удалось получить курс {crypto_slug} после 3 попыток.")


def generate_pending_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


async def remove_inline_buttons(message_list, bot, status_text: str):
    for admin_id, msg_id in message_list:
        try:
            await bot.edit_message_reply_markup(admin_id, msg_id, reply_markup=None)
        except:
            pass


def log_purchase(user_id: int, purchase_type: str, amount: int, price: float):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO purchase_logs (user_id, purchase_type, amount, price)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, purchase_type, amount, price),
        )
        conn.commit()
