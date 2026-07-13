import asyncio
import logging

from aiogram import Bot
from telethon import TelegramClient, events

import database as db
from config import Settings
from notifications import MatchEvent, NotificationService
from utils import find_matched_keywords, get_message_link

logger = logging.getLogger(__name__)


class ChatMonitor:
    def __init__(
        self,
        settings: Settings,
        telethon_client: TelegramClient,
        bot: Bot,
        notifier: NotificationService,
    ) -> None:
        self.settings = settings
        self.client = telethon_client
        self.bot = bot
        self.notifier = notifier
        self._backup_task: asyncio.Task | None = None
        self._running = False
        self._handler = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> bool:
        if self._running:
            return False

        if not self.client.is_connected():
            await self.client.connect()

        if not await self.client.is_user_authorized():
            raise RuntimeError(
                "Telethon-сессия не авторизована. Запустите main.py и войдите в аккаунт."
            )

        await self.notifier.refresh_settings()
        await self._catch_up_all_chats()

        if self._handler is None:
            self._handler = self._on_new_message
            self.client.add_event_handler(self._handler, events.NewMessage())

        self._running = True
        await db.set_monitor_running(True)
        self._backup_task = asyncio.create_task(self._backup_poll_loop(), name="chat-monitor-backup")
        logger.info("Мониторинг запущен (realtime + резервный опрос)")
        return True

    async def stop(self) -> None:
        self._running = False
        if self._backup_task and not self._backup_task.done():
            self._backup_task.cancel()
            try:
                await self._backup_task
            except asyncio.CancelledError:
                pass
        self._backup_task = None
        await db.set_monitor_running(False)
        await self.notifier.stop()
        logger.info("Мониторинг остановлен")

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        if not self._running:
            return

        chat = await db.get_active_chat(event.chat_id)
        if chat is None:
            return

        keywords = await db.get_all_keywords()
        if not keywords:
            return

        message = event.message
        text = message.text or message.message or ""
        matched = find_matched_keywords(text, keywords)
        if not matched:
            if message.id > chat.last_message_id:
                await db.update_last_message_id(chat.chat_id, message.id)
            return

        await self._dispatch_match(chat, message, text, matched)

    async def _backup_poll_loop(self) -> None:
        failures = 0
        poll_interval = self.settings.poll_interval
        try:
            while self._running:
                try:
                    bot_settings = await db.get_bot_settings()
                    poll_interval = bot_settings.poll_interval
                    await asyncio.sleep(poll_interval)
                    if not self._running:
                        break
                    await self._catch_up_all_chats()
                    failures = 0
                except asyncio.CancelledError:
                    raise
                except Exception:
                    failures += 1
                    delay = min(60, poll_interval * min(failures, 6))
                    logger.exception(
                        "Ошибка в резервном цикле мониторинга (попытка %s), повтор через %s сек",
                        failures,
                        delay,
                    )
                    await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise

    async def _catch_up_all_chats(self) -> None:
        chats = await db.get_active_chats()
        keywords = await db.get_all_keywords()
        if not chats or not keywords:
            return

        for chat in chats:
            try:
                await self._check_chat(chat, keywords)
            except Exception:
                logger.exception("Ошибка при проверке чата %s", chat.chat_id)

    async def _check_chat(self, chat, keywords: list[str]) -> None:
        messages = await self.client.get_messages(
            chat.chat_id,
            min_id=chat.last_message_id,
            limit=100,
        )
        if not messages:
            return

        messages.sort(key=lambda item: item.id)
        max_id = chat.last_message_id

        for message in messages:
            if message.id <= chat.last_message_id:
                continue

            text = message.text or message.message or ""
            matched = find_matched_keywords(text, keywords)
            if matched:
                await self._dispatch_match(chat, message, text, matched)

            max_id = max(max_id, message.id)

        if max_id > chat.last_message_id:
            await db.update_last_message_id(chat.chat_id, max_id)

    async def _dispatch_match(self, chat, message, text: str, matched: list[str]) -> None:
        message_link = await get_message_link(
            self.client,
            chat.chat_id,
            message.id,
            chat.username,
            message=message,
        )
        await self.notifier.notify(
            MatchEvent(
                chat_id=chat.chat_id,
                chat_title=chat.title,
                chat_type=chat.chat_type,
                username=chat.username,
                message_id=message.id,
                text=text,
                matched_keywords=matched,
                message_link=message_link,
            )
        )
        await db.update_last_message_id(chat.chat_id, message.id)
