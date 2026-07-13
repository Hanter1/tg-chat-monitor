import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class CallbackGuardMiddleware(BaseMiddleware):
    """Отвечает на callback, если handler не сделал этого сам."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Ошибка callback handler: data=%r", event.data)
            raise
        finally:
            try:
                await event.answer()
            except Exception:
                pass
