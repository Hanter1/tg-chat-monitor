import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    api_id: int
    api_hash: str
    telethon_session: str
    admin_user_id: int
    database_url: str
    poll_interval: int


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN")
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    admin_user_id = os.getenv("ADMIN_USER_ID")

    if not bot_token:
        raise ValueError("BOT_TOKEN не задан в .env")
    if not api_id or not api_hash:
        raise ValueError("API_ID и API_HASH не заданы в .env")
    if not admin_user_id:
        raise ValueError("ADMIN_USER_ID не задан в .env")

    return Settings(
        bot_token=bot_token,
        api_id=int(api_id),
        api_hash=api_hash,
        telethon_session=os.getenv("TELETHON_SESSION", "monitor_session"),
        admin_user_id=int(admin_user_id),
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./monitor.db"),
        poll_interval=int(os.getenv("POLL_INTERVAL", "10")),
    )
