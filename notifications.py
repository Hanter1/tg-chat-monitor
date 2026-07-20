from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Any

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from telethon import TelegramClient

import database as db
from services.message_forward import forward_message_to_bot

logger = logging.getLogger(__name__)

DIGEST_INTERVALS = {
    "instant": 0,
    "digest_15": 15 * 60,
    "digest_60": 60 * 60,
}

NOTIFY_MODE_LABELS = {
    "instant": "⚡ Сразу",
    "digest_15": "📦 Каждые 15 мин",
    "digest_60": "📦 Каждый час",
}

MatchSink = Callable[["MatchEvent"], Awaitable[None] | None]


@dataclass
class MatchEvent:
    chat_id: int
    chat_title: str
    chat_type: str
    username: str | None
    message_id: int
    text: str
    matched_keywords: list[str]
    message_link: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NotificationService:
    def __init__(
        self,
        bot: Bot | None,
        admin_user_id: int,
        *,
        telethon: TelegramClient | None = None,
        bot_username: str | None = None,
        on_match: MatchSink | None = None,
        telegram_notify: bool = True,
    ) -> None:
        self.bot = bot
        self.admin_user_id = admin_user_id
        self.telethon = telethon
        self.bot_username = bot_username
        self.on_match = on_match
        self._telegram_notify = telegram_notify
        self._pending: list[MatchEvent] = []
        self._digest_task: asyncio.Task | None = None
        self._notify_mode = "instant"

    @property
    def telegram_enabled(self) -> bool:
        return self.bot is not None and self._telegram_notify and self.admin_user_id > 0

    async def refresh_settings(self) -> None:
        bot_settings = await db.get_bot_settings()
        self._notify_mode = bot_settings.notify_mode
        self._telegram_notify = bool(
            getattr(bot_settings, "telegram_notify", self._telegram_notify)
        )

    async def notify(self, event: MatchEvent, *, historical: bool = False) -> bool:
        is_new = await db.log_match(
            chat_id=event.chat_id,
            chat_title=event.chat_title,
            message_id=event.message_id,
            text_preview=event.text,
            keywords=",".join(event.matched_keywords),
            message_link=event.message_link,
        )
        if not is_new:
            return False

        await self._emit_local(event)

        if not self.telegram_enabled:
            return True

        if historical or self._notify_mode == "instant":
            await self._send_single(event, historical=historical)
            return True

        self._pending.append(event)
        if self._digest_task is None or self._digest_task.done():
            self._digest_task = asyncio.create_task(self._digest_loop())
        return True

    async def _emit_local(self, event: MatchEvent) -> None:
        if self.on_match is None:
            return
        try:
            result = self.on_match(event)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("Local match sink failed")

    async def flush_digest(self) -> None:
        if not self._pending:
            return
        from html import escape

        from bot_ui import open_message_callback, truncate

        batch = self._pending[:]
        self._pending.clear()

        if not self.telegram_enabled:
            return

        lines = [
            f"📦 <b>Дайджест — {len(batch)} совпадений</b>",
            "",
        ]
        buttons: list[list[InlineKeyboardButton]] = []

        for index, event in enumerate(batch[:15], start=1):
            preview = escape(truncate(event.text, 80))
            words = ", ".join(f"<code>{escape(w)}</code>" for w in event.matched_keywords)
            lines.append(
                f"<b>{index}.</b> {escape(truncate(event.chat_title, 32))}\n"
                f"🔑 {words}\n"
                f"💬 {preview}"
            )
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📎 {index}. {truncate(event.chat_title, 20)}",
                        callback_data=open_message_callback(event.chat_id, event.message_id),
                    )
                ]
            )

        if len(batch) > 15:
            lines.append(f"\n<i>...и ещё {len(batch) - 15} совпадений в журнале (/matches)</i>")

        lines.append("\n<i>Кнопки 📎 перешлют сообщение в этот чат.</i>")

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons[:15]) if buttons else None
        assert self.bot is not None
        await self.bot.send_message(
            self.admin_user_id,
            "\n\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )

    async def stop(self) -> None:
        if self._digest_task and not self._digest_task.done():
            self._digest_task.cancel()
            try:
                await self._digest_task
            except asyncio.CancelledError:
                pass
        if self._pending:
            await self.flush_digest()

    async def _digest_loop(self) -> None:
        interval = DIGEST_INTERVALS.get(self._notify_mode, 0)
        if interval <= 0:
            return
        try:
            while True:
                await asyncio.sleep(interval)
                await self.flush_digest()
        except asyncio.CancelledError:
            if self._pending:
                await self.flush_digest()
            raise

    async def _forward_to_bot(self, event: MatchEvent) -> None:
        if not self.telethon or not self.bot_username:
            return
        await forward_message_to_bot(
            self.telethon,
            self.bot_username,
            event.chat_id,
            event.message_id,
            chat_title=event.chat_title,
            chat_type=event.chat_type,
            keywords=event.matched_keywords,
        )

    async def _send_single(self, event: MatchEvent, *, historical: bool) -> None:
        from bot_ui import format_match_notification

        if not self.telegram_enabled or self.bot is None:
            return

        notification, preview_options, keyboard = format_match_notification(
            title=event.chat_title,
            chat_type=event.chat_type,
            chat_id=event.chat_id,
            username=event.username,
            message_id=event.message_id,
            text=event.text,
            matched_keywords=event.matched_keywords,
            historical=historical,
            message_link=event.message_link,
        )
        await self.bot.send_message(
            self.admin_user_id,
            notification,
            parse_mode=ParseMode.HTML,
            link_preview_options=preview_options,
            reply_markup=keyboard,
        )
        await self._forward_to_bot(event)
