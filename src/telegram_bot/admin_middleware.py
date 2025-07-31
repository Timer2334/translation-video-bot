from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable, Dict, Any
from config.settings import ADMIN_IDS


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if event.from_user and event.from_user.id not in ADMIN_IDS:
            return
        return await handler(event, data)
