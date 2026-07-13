from aiogram import F, Router
from aiogram.types import CallbackQuery

import database as db
from handlers.context import BotContext
from handlers.filters import admin_callback_only, answer_callback
from services.message_forward import forward_message_to_bot


def register_open_message_handlers(ctx: BotContext) -> Router:
    router = Router(name="open_message")
    admin_cb_filter = admin_callback_only(ctx.settings)

    @router.callback_query(F.data.startswith("open:"), admin_cb_filter)
    async def cb_open_message(callback: CallbackQuery) -> None:
        parts = callback.data.split(":")
        if len(parts) != 3:
            await answer_callback(callback, "Некорректная ссылка", show_alert=True)
            return

        chat_id = int(parts[1])
        message_id = int(parts[2])

        if not ctx.bot_username:
            await answer_callback(callback, "Бот не настроен для пересылки", show_alert=True)
            return

        chat = await db.get_chat(chat_id)
        chat_title = chat.title if chat else f"Чат {chat_id}"
        chat_type = chat.chat_type if chat else "unknown"

        ok = await forward_message_to_bot(
            ctx.telethon,
            ctx.bot_username,
            chat_id,
            message_id,
            chat_title=chat_title,
            chat_type=chat_type,
        )
        if ok:
            await answer_callback(
                callback,
                f"Переслано из «{chat_title[:40]}»",
            )
        else:
            await answer_callback(
                callback,
                "Не удалось переслать. Возможно, сообщение удалено или нет доступа.",
                show_alert=True,
            )

    return router
