import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app_paths import default_database_url, env_path, get_data_dir


@dataclass(frozen=True)
class Settings:
    bot_token: str | None
    api_id: int
    api_hash: str
    telethon_session: str
    admin_user_id: int
    database_url: str
    poll_interval: int
    scan_history_limit: int
    scan_period_days: int
    scan_mode: str
    telegram_notify: bool
    allow_no_bot: bool


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_env_file(path: Path | None = None) -> None:
    """Загрузить .env из каталога данных (или указанного пути)."""
    target = path or env_path()
    load_dotenv(target, override=True)


def get_settings(*, env_file: Path | None = None) -> Settings:
    load_env_file(env_file)

    allow_no_bot = _env_flag("TG_MONITOR_ALLOW_NO_BOT")
    bot_token = (os.getenv("BOT_TOKEN") or "").strip() or None
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    admin_user_id_raw = (os.getenv("ADMIN_USER_ID") or "").strip()

    if not bot_token and not allow_no_bot:
        raise ValueError("BOT_TOKEN не задан в .env")
    if not api_id or not api_hash:
        raise ValueError("API_ID и API_HASH не заданы в .env")
    if not admin_user_id_raw and not allow_no_bot:
        raise ValueError("ADMIN_USER_ID не задан в .env")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = default_database_url()
    elif database_url.startswith("sqlite") and ":///" in database_url:
        # Относительный ./monitor.db → абсолютный путь в DATA_DIR
        prefix, _, rest = database_url.partition(":///")
        if rest.startswith("./") or (rest and not rest.startswith("/") and ":" not in rest[:3]):
            db_name = rest.removeprefix("./")
            abs_db = (get_data_dir() / db_name).resolve()
            database_url = f"{prefix}:///{abs_db.as_posix()}"

    telegram_notify_default = bool(bot_token) and not allow_no_bot
    telegram_notify = _env_flag("TELEGRAM_NOTIFY", default=telegram_notify_default)

    return Settings(
        bot_token=bot_token,
        api_id=int(api_id),
        api_hash=api_hash,
        telethon_session=os.getenv("TELETHON_SESSION", "monitor_session"),
        admin_user_id=int(admin_user_id_raw) if admin_user_id_raw else 0,
        database_url=database_url,
        poll_interval=int(os.getenv("POLL_INTERVAL", "10")),
        scan_history_limit=int(os.getenv("SCAN_HISTORY_LIMIT", "100")),
        scan_period_days=int(os.getenv("SCAN_PERIOD_DAYS", "7")),
        scan_mode=os.getenv("SCAN_MODE", "timeline"),
        telegram_notify=telegram_notify,
        allow_no_bot=allow_no_bot,
    )
