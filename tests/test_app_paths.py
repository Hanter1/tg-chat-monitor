"""Тесты каталога данных и загрузки настроек."""

from __future__ import annotations

from pathlib import Path

import pytest

import app_paths
from config import get_settings


@pytest.fixture(autouse=True)
def _clean_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    app_paths.reset_data_dir_cache()
    monkeypatch.delenv("TG_MONITOR_DATA_DIR", raising=False)
    for key in (
        "BOT_TOKEN",
        "API_ID",
        "API_HASH",
        "ADMIN_USER_ID",
        "DATABASE_URL",
        "TELETHON_SESSION",
        "POLL_INTERVAL",
    ):
        monkeypatch.delenv(key, raising=False)
    yield
    app_paths.reset_data_dir_cache()


def test_default_data_dir_is_project_root():
    assert app_paths.get_data_dir() == app_paths.get_project_root()


def test_set_data_dir_override(tmp_path: Path):
    target = tmp_path / "data"
    result = app_paths.set_data_dir(target)
    assert result == target.resolve()
    assert app_paths.get_data_dir() == target.resolve()
    assert app_paths.env_path() == target.resolve() / ".env"
    assert "monitor.db" in app_paths.default_database_url()


def test_telethon_session_path_relative(tmp_path: Path):
    app_paths.set_data_dir(tmp_path)
    path = app_paths.telethon_session_path("mysession")
    assert Path(path) == (tmp_path / "mysession").resolve()


def test_get_settings_from_data_dir_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    app_paths.set_data_dir(tmp_path)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BOT_TOKEN=123:abc",
                "API_ID=42",
                "API_HASH=hash",
                "ADMIN_USER_ID=7",
                "DATABASE_URL=sqlite+aiosqlite:///./monitor.db",
                "TELETHON_SESSION=sess",
                "POLL_INTERVAL=15",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    settings = get_settings()
    assert settings.bot_token == "123:abc"
    assert settings.api_id == 42
    assert settings.admin_user_id == 7
    assert settings.poll_interval == 15
    assert str(tmp_path.resolve().as_posix()) in settings.database_url.replace("\\", "/")
    assert settings.telethon_session == "sess"


def test_env_var_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TG_MONITOR_DATA_DIR", str(tmp_path))
    app_paths.reset_data_dir_cache()
    assert app_paths.get_data_dir() == tmp_path.resolve()
