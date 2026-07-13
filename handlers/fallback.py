from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

import bot_ui as ui
from handlers.context import BotContext
from handlers.filters import admin_only


def register_fallback_handlers(ctx: BotContext) -> Router:
    router = Router(name="fallback")
    admin_filter = admin_only(ctx.settings)

    @router.message(F.chat.type == ChatType.PRIVATE, admin_filter)
    async def unknown_private(message: Message) -> None:
        if message.text and message.text.startswith("/"):
            await message.answer(
                "Неизвестная команда. Откройте /menu",
                reply_markup=ui.back_to_menu_keyboard(),
            )

    return router
