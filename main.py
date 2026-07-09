import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from telethon import TelegramClient

import database as db
from bot import create_dispatcher
from config import get_settings
from monitor import ChatMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def ensure_telethon_authorized(client: TelegramClient) -> None:
    await client.connect()
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


async def main() -> None:
    settings = get_settings()

    db.init_db(settings.database_url)
    await db.create_tables()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    telethon_client = TelegramClient(
        settings.telethon_session,
        settings.api_id,
        settings.api_hash,
    )

    await ensure_telethon_authorized(telethon_client)

    monitor = ChatMonitor(settings, telethon_client, bot)
    dp = await create_dispatcher(settings, monitor)

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


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
