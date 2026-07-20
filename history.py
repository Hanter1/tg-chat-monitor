"""Поиск совпадений в истории переписки."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import Message
from telethon import TelegramClient

import database as db
from config import Settings
from notifications import MatchEvent, NotificationService
from services.scan_config import ScanConfig
from services.scan_dates import message_date_utc, message_in_scan_period, utc_cutoff
from utils import find_matched_keywords, get_message_link

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanResult:
    chats_scanned: int
    matches_found: int
    matches_sent: int
    matches_skipped: int
    config: ScanConfig


class HistoryScanner:
    MAX_NOTIFICATIONS = 35

    def __init__(
        self,
        settings: Settings,
        telethon_client: TelegramClient,
        bot: Bot | None,
        notifier: NotificationService,
    ) -> None:
        self.settings = settings
        self.client = telethon_client
        self.bot = bot
        self.notifier = notifier
        self._scan_lock = asyncio.Lock()

    @property
    def is_scanning(self) -> bool:
        return self._scan_lock.locked()

    async def scan(
        self,
        *,
        chat_id: int | None = None,
        config: ScanConfig | None = None,
        progress_message: Message | None = None,
    ) -> ScanResult:
        if self._scan_lock.locked():
            raise RuntimeError("Мониторинг уже выполняется. Дождитесь завершения.")

        if config is None:
            config = ScanConfig.from_bot_settings(await db.get_bot_settings())
        else:
            config = config.normalized()

        async with self._scan_lock:
            return await self._run_scan(
                chat_id=chat_id,
                config=config,
                progress_message=progress_message,
            )

    async def _run_scan(
        self,
        *,
        chat_id: int | None,
        config: ScanConfig,
        progress_message: Message | None,
    ) -> ScanResult:
        if not self.client.is_connected():
            await self.client.connect()

        chats = await db.get_all_chats()
        keywords = await db.get_all_keywords()

        if chat_id is not None:
            chats = [chat for chat in chats if chat.chat_id == chat_id]
            if not chats:
                raise ValueError("Чат не найден в списке мониторинга")

        if not chats:
            raise ValueError("Список чатов пуст. Добавьте группы через /add_chat")
        if not keywords:
            raise ValueError("Ключевые слова не заданы. Добавьте через /add_word")

        matches_found = 0
        matches_sent = 0
        matches_skipped = 0

        await self._update_progress(
            progress_message,
            self._format_progress(
                config=config,
                chats_total=len(chats),
                chat_index=0,
                chat_title="",
                matches_found=0,
                phase="Старт...",
            ),
        )

        for index, chat in enumerate(chats, start=1):
            await self._update_progress(
                progress_message,
                self._format_progress(
                    config=config,
                    chats_total=len(chats),
                    chat_index=index,
                    chat_title=chat.title,
                    matches_found=matches_found,
                    phase="Проверяю",
                ),
            )

            if config.mode == "search":
                chat_matches = await self._scan_chat_search(chat, keywords, config)
            else:
                chat_matches = await self._scan_chat_timeline(chat, keywords, config)

            matches_found += len(chat_matches)

            for message, text, matched in chat_matches:
                if matches_sent >= self.MAX_NOTIFICATIONS:
                    matches_skipped += 1
                    continue

                message_link = await get_message_link(
                    self.client,
                    chat.chat_id,
                    message.id,
                    chat.username,
                    message=message,
                )
                sent = await self.notifier.notify(
                    MatchEvent(
                        chat_id=chat.chat_id,
                        chat_title=chat.title,
                        chat_type=chat.chat_type,
                        username=chat.username,
                        message_id=message.id,
                        text=text,
                        matched_keywords=matched,
                        message_link=message_link,
                    ),
                    historical=True,
                )
                if sent:
                    matches_sent += 1
                    await asyncio.sleep(0.35)
                else:
                    matches_skipped += 1

            await asyncio.sleep(0.5)

        await self._update_progress(
            progress_message,
            self._format_summary(
                chats_scanned=len(chats),
                matches_found=matches_found,
                matches_sent=matches_sent,
                matches_skipped=matches_skipped,
                config=config,
            ),
        )

        return ScanResult(
            chats_scanned=len(chats),
            matches_found=matches_found,
            matches_sent=matches_sent,
            matches_skipped=matches_skipped,
            config=config,
        )

    async def _scan_chat_timeline(
        self, chat, keywords: list[str], config: ScanConfig
    ) -> list[tuple]:
        cutoff = utc_cutoff(config.period_days)
        seen_ids: set[int] = set()
        results: list[tuple] = []
        checked = 0

        async for message in self.client.iter_messages(chat.chat_id):
            if checked >= config.limit_per_chat:
                break
            if message_date_utc(message) < cutoff:
                break

            checked += 1
            if message.id in seen_ids:
                continue

            text = message.text or message.message or ""
            matched = find_matched_keywords(text, keywords)
            if not matched:
                continue

            seen_ids.add(message.id)
            results.append((message, text, matched))

        results.sort(key=lambda item: item[0].id, reverse=True)
        return results

    async def _scan_chat_search(
        self, chat, keywords: list[str], config: ScanConfig
    ) -> list[tuple]:
        seen_ids: set[int] = set()
        results: list[tuple] = []

        for keyword in keywords:
            try:
                async for message in self.client.iter_messages(
                    chat.chat_id,
                    search=keyword,
                    limit=config.limit_per_chat,
                ):
                    if not message_in_scan_period(message, config.period_days):
                        continue
                    if message.id in seen_ids:
                        continue

                    text = message.text or message.message or ""
                    matched = find_matched_keywords(text, keywords)
                    if not matched:
                        continue

                    seen_ids.add(message.id)
                    results.append((message, text, matched))
            except Exception:
                logger.exception("Ошибка поиска в чате %s по слову %s", chat.chat_id, keyword)

        results.sort(key=lambda item: item[0].id, reverse=True)
        return results

    def _format_progress(
        self,
        *,
        config: ScanConfig,
        chats_total: int,
        chat_index: int,
        chat_title: str,
        matches_found: int,
        phase: str,
    ) -> str:
        lines = [
            "🔍 <b>Мониторинг</b>",
            "",
            config.summary_line(),
            "",
        ]
        if chat_index:
            lines.append(f"📂 Чат <b>{chat_index}/{chats_total}</b>: {escape_title(chat_title)}")
        lines.extend(
            [
                f"🔎 Найдено: <b>{matches_found}</b>",
                f"<i>{phase}</i>",
            ]
        )
        return "\n".join(lines)

    async def _update_progress(self, progress_message: Message | None, text: str) -> None:
        if progress_message is None:
            return
        try:
            await progress_message.edit_text(text)
        except Exception:
            logger.debug("Не удалось обновить статус поиска", exc_info=True)

    def _format_summary(
        self,
        *,
        chats_scanned: int,
        matches_found: int,
        matches_sent: int,
        matches_skipped: int,
        config: ScanConfig,
    ) -> str:
        lines = [
            "✅ <b>Мониторинг завершён</b>",
            "",
            config.summary_line(),
            "",
            f"📂 Проверено чатов: <b>{chats_scanned}</b>",
            f"🔎 Найдено совпадений: <b>{matches_found}</b>",
            f"📨 Отправлено уведомлений: <b>{matches_sent}</b>",
        ]
        if matches_skipped:
            lines.append(
                f"\n⚠️ Ещё <b>{matches_skipped}</b> совпадений пропущено "
                f"(лимит {self.MAX_NOTIFICATIONS} за один запуск).\n"
                f"Сузьте период, выберите один чат или запустите снова."
            )
        if matches_found == 0:
            lines.append("\n<i>В выбранном периоде совпадений не найдено.</i>")
        return "\n".join(lines)


def escape_title(title: str) -> str:
    from html import escape

    from bot_ui import truncate

    return escape(truncate(title, 40))
