import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

from config.settings import TOKEN, api_server_link
from src.telegram_bot.db import init_db
from src.telegram_bot.handlers import register_all_handlers
from src.telegram_bot.admin import router_admin
from src.telegram_bot.payment import router_payment, setup_payment_routes, start_crypto_invoices_task
from src.telegram_bot.watchers import watch_translated_folder

async def main():
    logging.basicConfig(level=logging.INFO)

    # Создаём Bot и сразу сбрасываем все накопленные апдейты
    bot = Bot(
        token=TOKEN,
        session=AiohttpSession(api=TelegramAPIServer.from_base(api_server_link)),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.delete_webhook(drop_pending_updates=True)

    # Диспетчер с in‑memory хранением
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем обработчики команд и колбэков
    register_all_handlers(dp)
    dp.include_router(router_admin)

    # Настраиваем механизм оплаты (передаём в watcher платежей общую dict для state)
    user_db = {}
    setup_payment_routes(user_db)
    dp.include_router(router_payment)

    # Хук on_startup для фоновых задач
    async def on_startup(dispatcher: Dispatcher):
        logging.info("Startup: initializing database and launching background tasks")
        init_db()
        # watcher, который игнорирует существующие файлы при старте
        asyncio.create_task(watch_translated_folder(bot))
        # таск для проверки и отправки крипто‑счетов
        asyncio.create_task(start_crypto_invoices_task(bot, user_db))

    dp.startup.register(on_startup)

    # Запускаем polling без skip_updates
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
