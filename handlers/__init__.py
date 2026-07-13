from aiogram import Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from telethon import TelegramClient

from config import Settings
from handlers.chats import register_chat_handlers
from handlers.context import BotContext
from handlers.fallback import register_fallback_handlers
from handlers.history_cmds import register_history_handlers
from handlers.menu import register_menu_handlers
from handlers.middleware import CallbackGuardMiddleware
from handlers.monitor_cmds import register_monitor_handlers
from handlers.open_message import register_open_message_handlers
from handlers.settings_cmds import register_settings_handlers
from handlers.words import register_word_handlers
from history import HistoryScanner
from monitor import ChatMonitor
from notifications import NotificationService


def setup_router(
    settings: Settings,
    monitor: ChatMonitor,
    telethon: TelegramClient,
    history_scanner: HistoryScanner,
    notifier: NotificationService,
    bot_username: str | None = None,
) -> Router:
    ctx = BotContext(
        settings=settings,
        monitor=monitor,
        telethon=telethon,
        history_scanner=history_scanner,
        notifier=notifier,
        bot_username=bot_username,
    )

    root = Router()
    root.callback_query.middleware(CallbackGuardMiddleware())

    root.include_router(register_menu_handlers(ctx))
    root.include_router(register_chat_handlers(ctx))
    root.include_router(register_word_handlers(ctx))
    root.include_router(register_settings_handlers(ctx))
    root.include_router(register_monitor_handlers(ctx))
    root.include_router(register_history_handlers(ctx))
    root.include_router(register_open_message_handlers(ctx))
    root.include_router(register_fallback_handlers(ctx))
    return root


async def create_dispatcher(
    settings: Settings,
    monitor: ChatMonitor,
    telethon: TelegramClient,
    history_scanner: HistoryScanner,
    notifier: NotificationService,
    bot_username: str | None = None,
) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(
        setup_router(settings, monitor, telethon, history_scanner, notifier, bot_username)
    )
    return dp
