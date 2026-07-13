import asyncio
import logging
import sqlite3
import sys
from pathlib import Path

if __name__ == "__main__":
    _project_root = Path(__file__).resolve().parent
    _env_path = _project_root / ".env"
    if not _env_path.exists():
        print()
        print("=" * 60)
        print("  Файл .env не найден")
        print("=" * 60)
        print()
        print("  Запустите мастер настройки:")
        print("    python setup.py")
        print()
        print("  Или вручную скопируйте шаблон:")
        print("    cp .env.example .env   (Linux/macOS)")
        print("    copy .env.example .env   (Windows)")
        print()
        sys.exit(1)

    from instance_lock import acquire_single_instance_lock

    acquire_single_instance_lock(_project_root)

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from telethon import TelegramClient

import database as db
from bot import create_dispatcher
from config import get_settings
from history import HistoryScanner
from instance_lock import release_single_instance_lock
from monitor import ChatMonitor
from notifications import NotificationService
from telethon_session import ResilientSQLiteSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def ensure_telethon_authorized(client: TelegramClient) -> None:
    last_error: Exception | None = None

    for attempt in range(5):
        try:
            await client.connect()
            break
        except sqlite3.OperationalError as exc:
            last_error = exc
            if "locked" not in str(exc).lower() or attempt == 4:
                raise
            wait_seconds = 2 * (attempt + 1)
            logger.warning(
                "Файл сессии Telethon занят, повтор через %s сек... (%s/5)",
                wait_seconds,
                attempt + 1,
            )
            await asyncio.sleep(wait_seconds)
    else:
        if last_error:
            raise last_error

    if await client.is_user_authorized():
        logger.info("Telethon-сессия авторизована")
        return

    phone = input("Введите номер телефона Telethon (международный формат, +7...): ").strip()
    await client.send_code_request(phone)
    code = input("Введите код из Telegram: ").strip()

    try:
        await client.sign_in(phone, code)
    except Exception:
        password = input("Введите пароль двухфакторной аутентификации: ").strip()
        await client.sign_in(password=password)

    logger.info("Telethon авторизация успешна")


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


async def main() -> None:
    settings = get_settings()

    db.init_db(settings.database_url)
    await db.create_tables(env_defaults=settings)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    bot_me = await bot.get_me()

    telethon_client = TelegramClient(
        ResilientSQLiteSession(settings.telethon_session),
        settings.api_id,
        settings.api_hash,
    )

    await ensure_telethon_authorized(telethon_client)

    notifier = NotificationService(
        bot,
        settings.admin_user_id,
        telethon=telethon_client,
        bot_username=bot_me.username,
    )
    await notifier.refresh_settings()
    monitor = ChatMonitor(settings, telethon_client, bot, notifier)
    history_scanner = HistoryScanner(settings, telethon_client, bot, notifier)
    dp = await create_dispatcher(
        settings,
        monitor,
        telethon_client,
        history_scanner,
        notifier,
        bot_username=bot_me.username,
    )

    await setup_bot_commands(bot, settings.admin_user_id)

    if await db.is_monitor_running():
        logger.info("Восстанавливаем мониторинг после перезапуска")
        try:
            await monitor.start()
        except Exception:
            logger.exception("Не удалось восстановить мониторинг")

    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await monitor.stop()
        await telethon_client.disconnect()
        await bot.session.close()
        release_single_instance_lock()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
