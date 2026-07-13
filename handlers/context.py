from dataclasses import dataclass

from telethon import TelegramClient

from config import Settings
from history import HistoryScanner
from monitor import ChatMonitor
from notifications import NotificationService


@dataclass(frozen=True)
class BotContext:
    settings: Settings
    monitor: ChatMonitor
    telethon: TelegramClient
    history_scanner: HistoryScanner
    notifier: NotificationService
    bot_username: str | None = None
