import asyncio
import logging

from aiogram import Bot
from telethon import TelegramClient
from telethon.tl.types import Message as TelethonMessage

import database as db
from config import Settings
from utils import build_message_link, message_contains_keyword

logger = logging.getLogger(__name__)


class ChatMonitor:
    def __init__(
        self,
        settings: Settings,
        telethon_client: TelegramClient,
        bot: Bot,
    ) -> None:
        self.settings = settings
        self.client = telethon_client
        self.bot = bot
        self._task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> bool:
        if self.is_running:
            return False

        if not self.client.is_connected():
            await self.client.connect()

        if not await self.client.is_user_authorized():
            raise RuntimeError(
                "Telethon-сессия не авторизована. Запустите main.py и войдите в аккаунт."
            )

        await db.set_monitor_running(True)
        self._task = asyncio.create_task(self._poll_loop(), name="chat-monitor")
        logger.info("Мониторинг запущен")
        return True

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        await db.set_monitor_running(False)
        logger.info("Мониторинг остановлен")

    async def _poll_loop(self) -> None:
        try:
            while True:
                await self._check_all_chats()
                await asyncio.sleep(self.settings.poll_interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка в цикле мониторинга")
            await db.set_monitor_running(False)
            raise

    async def _check_all_chats(self) -> None:
        chats = await db.get_all_chats()
        keywords = await db.get_all_keywords()

        if not chats or not keywords:
            return

        for chat in chats:
            try:
                await self._check_chat(chat, keywords)
            except Exception:
                logger.exception("Ошибка при проверке чата %s", chat.chat_id)

    async def _check_chat(self, chat, keywords: list[str]) -> None:
        messages: list[TelethonMessage] = await self.client.get_messages(
            chat.chat_id,
            min_id=chat.last_message_id,
            limit=50,
        )

        if not messages:
            return

        messages.sort(key=lambda m: m.id)

        max_id = chat.last_message_id
        for message in messages:
            if message.id <= chat.last_message_id:
                continue

            text = message.text or message.message or ""
            if message_contains_keyword(text, keywords):
                link = build_message_link(chat.chat_id, message.id, chat.username)
                notification = (
                    f"🔔 Найдено в чате {chat.title}: {text}\n"
                    f"Ссылка: {link}"
                )
                await self.bot.send_message(self.settings.admin_user_id, notification)

            max_id = max(max_id, message.id)

        if max_id > chat.last_message_id:
            await db.update_last_message_id(chat.chat_id, max_id)
