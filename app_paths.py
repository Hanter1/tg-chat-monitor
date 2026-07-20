"""Единая точка для каталога данных (.env, DB, Telethon session)."""

from __future__ import annotations

import os
from pathlib import Path

_ENV_DATA_DIR = "TG_MONITOR_DATA_DIR"
_data_dir: Path | None = None


def get_project_root() -> Path:
    return Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """Каталог записи: env TG_MONITOR_DATA_DIR или корень проекта."""
    global _data_dir
    if _data_dir is not None:
        return _data_dir

    override = os.environ.get(_ENV_DATA_DIR, "").strip()
    if override:
        path = Path(override).expanduser().resolve()
    else:
        path = get_project_root()

    path.mkdir(parents=True, exist_ok=True)
    _data_dir = path
    return path


def set_data_dir(path: Path | str) -> Path:
    """Задать каталог данных (Android / тесты)."""
    global _data_dir
    resolved = Path(path).expanduser().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    os.environ[_ENV_DATA_DIR] = str(resolved)
    _data_dir = resolved
    return resolved


def reset_data_dir_cache() -> None:
    """Сброс кэша (только для тестов)."""
    global _data_dir
    _data_dir = None


def env_path() -> Path:
    return get_data_dir() / ".env"


def default_database_url() -> str:
    db_file = (get_data_dir() / "monitor.db").resolve()
    return f"sqlite+aiosqlite:///{db_file.as_posix()}"


def telethon_session_path(session_name: str) -> str:
    """Абсолютный путь к файлу сессии Telethon (без суффикса .session)."""
    name = session_name.strip() or "monitor_session"
    if Path(name).is_absolute():
        return name
    return str((get_data_dir() / name).resolve())
