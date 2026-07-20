"""Запуск приложения: общий код для CLI и Android."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from telethon import TelegramClient

import database as db
from app_paths import telethon_session_path
from bot import create_dispatcher
from config import Settings, get_settings
from history import HistoryScanner
from monitor import ChatMonitor
from notifications import MatchSink, NotificationService
from runtime_state import RuntimeHandle, set_runtime_handle
from telethon_auth import AuthPrompter, ensure_telethon_authorized
from telethon_session import ResilientSQLiteSession

logger = logging.getLogger(__name__)

OnReadyFn = Callable[[], Awaitable[None] | None]


async def setup_bot_commands(bot: Bot, admin_user_id: int) -> None:
    from aiogram.types import BotCommand, BotCommandScopeChat

    commands = [
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="status", description="Статус мониторинга"),
        BotCommand(command="add_chat", description="Добавить чат / группу"),
        BotCommand(command="add_word", description="Добавить ключевое слово"),
        BotCommand(command="scan", description="Мониторинг / сканирование"),
        BotCommand(command="matches", description="Журнал находок"),
        BotCommand(command="settings", description="Настройки"),
        BotCommand(command="help", description="Справка"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=admin_user_id))


async def run_app(
    *,
    settings: Settings | None = None,
    auth_prompter: AuthPrompter | None = None,
    on_ready: OnReadyFn | None = None,
    release_lock: Callable[[], None] | None = None,
    match_sink: MatchSink | None = None,
) -> None:
    """Полный цикл: Telethon + (опционально) aiogram polling до остановки."""
    cfg = settings or get_settings()

    db.init_db(cfg.database_url)
    await db.create_tables(env_defaults=cfg)

    bot: Bot | None = None
    bot_username: str | None = None
    if cfg.bot_token:
        bot = Bot(
            token=cfg.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        bot_me = await bot.get_me()
        bot_username = bot_me.username

    session_path = telethon_session_path(cfg.telethon_session)
    telethon_client = TelegramClient(
        ResilientSQLiteSession(session_path),
        cfg.api_id,
        cfg.api_hash,
    )

    await ensure_telethon_authorized(telethon_client, prompter=auth_prompter)

    admin_user_id = cfg.admin_user_id
    if admin_user_id <= 0:
        me = await telethon_client.get_me()
        admin_user_id = int(me.id)
        logger.info("ADMIN_USER_ID авто: %s", admin_user_id)
        from dataclasses import replace

        cfg = replace(cfg, admin_user_id=admin_user_id)

    notifier = NotificationService(
        bot,
        admin_user_id,
        telethon=telethon_client,
        bot_username=bot_username,
        on_match=match_sink,
        telegram_notify=cfg.telegram_notify,
    )
    await notifier.refresh_settings()
    monitor = ChatMonitor(cfg, telethon_client, bot, notifier)
    history_scanner = HistoryScanner(cfg, telethon_client, bot, notifier)

    set_runtime_handle(
        RuntimeHandle(
            settings=cfg,
            telethon=telethon_client,
            monitor=monitor,
            notifier=notifier,
            history_scanner=history_scanner,
            bot=bot,
            admin_user_id=admin_user_id,
        )
    )

    if await db.is_monitor_running():
        logger.info("Восстанавливаем мониторинг после перезапуска")
        try:
            await monitor.start()
        except Exception:
            logger.exception("Не удалось восстановить мониторинг")

    if on_ready is not None:
        result = on_ready()
        if asyncio_is_awaitable(result):
            await result  # type: ignore[misc]

    try:
        if bot is not None:
            dp = await create_dispatcher(
                cfg,
                monitor,
                telethon_client,
                history_scanner,
                notifier,
                bot_username=bot_username,
            )
            if admin_user_id > 0:
                await setup_bot_commands(bot, admin_user_id)
            logger.info("Бот запущен")
            await dp.start_polling(bot)
        else:
            logger.info("Режим без бота: Telethon + monitor")
            await asyncio.Event().wait()
    finally:
        set_runtime_handle(None)
        await monitor.stop()
        await telethon_client.disconnect()
        if bot is not None:
            await bot.session.close()
        if release_lock is not None:
            release_lock()


def asyncio_is_awaitable(value: object) -> bool:
    import inspect

    return inspect.isawaitable(value)


# re-export for type checkers / callers
__all__ = ["run_app", "setup_bot_commands"]
