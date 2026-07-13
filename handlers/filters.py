import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import Settings

logger = logging.getLogger(__name__)


class AdminMessageFilter(BaseFilter):
    def __init__(self, admin_user_id: int) -> None:
        self.admin_user_id = admin_user_id

    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id == self.admin_user_id


class AdminCallbackFilter(BaseFilter):
    def __init__(self, admin_user_id: int) -> None:
        self.admin_user_id = admin_user_id

    async def __call__(self, callback: CallbackQuery) -> bool:
        return callback.from_user is not None and callback.from_user.id == self.admin_user_id


def admin_only(settings: Settings) -> AdminMessageFilter:
    return AdminMessageFilter(settings.admin_user_id)


def admin_callback_only(settings: Settings) -> AdminCallbackFilter:
    return AdminCallbackFilter(settings.admin_user_id)


async def safe_edit_text(message: Message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            if kwargs.get("reply_markup") is not None:
                try:
                    await message.edit_reply_markup(reply_markup=kwargs["reply_markup"])
                except TelegramBadRequest as markup_exc:
                    if "message is not modified" not in str(markup_exc).lower():
                        raise
            return
        raise


async def safe_edit_callback(callback: CallbackQuery, text: str, **kwargs) -> None:
    await safe_edit_text(callback.message, text, **kwargs)


async def answer_callback(callback: CallbackQuery, *args, **kwargs) -> None:
    try:
        await callback.answer(*args, **kwargs)
    except TelegramBadRequest as exc:
        if "query is too old" in str(exc).lower() or "query id is invalid" in str(exc).lower():
            return
        raise


async def answer_callback_safe(callback: CallbackQuery, *args, **kwargs) -> None:
    try:
        await callback.answer(*args, **kwargs)
    except TelegramBadRequest:
        pass
