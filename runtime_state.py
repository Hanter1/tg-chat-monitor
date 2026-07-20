"""Глобальный runtime-handle для Android bridge / app API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Bot
    from telethon import TelegramClient

    from config import Settings
    from history import HistoryScanner
    from monitor import ChatMonitor
    from notifications import NotificationService


@dataclass
class RuntimeHandle:
    settings: Settings
    telethon: TelegramClient
    monitor: ChatMonitor
    notifier: NotificationService
    history_scanner: HistoryScanner
    bot: Bot | None
    admin_user_id: int


_handle: RuntimeHandle | None = None


def get_runtime_handle() -> RuntimeHandle | None:
    return _handle


def set_runtime_handle(handle: RuntimeHandle | None) -> None:
    global _handle
    _handle = handle
