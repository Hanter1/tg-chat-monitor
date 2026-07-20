from pathlib import Path

import pytest

from config import get_settings


def test_allow_no_bot_without_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TG_MONITOR_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TG_MONITOR_ALLOW_NO_BOT", "1")
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("ADMIN_USER_ID", raising=False)
    monkeypatch.setenv("API_ID", "42")
    monkeypatch.setenv("API_HASH", "hash")
    monkeypatch.setenv("TELEGRAM_NOTIFY", "0")

    from app_paths import reset_data_dir_cache

    reset_data_dir_cache()
    settings = get_settings()
    assert settings.bot_token is None
    assert settings.allow_no_bot is True
    assert settings.admin_user_id == 0
    assert settings.telegram_notify is False


def test_bot_still_required_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TG_MONITOR_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("TG_MONITOR_ALLOW_NO_BOT", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("API_ID", "42")
    monkeypatch.setenv("API_HASH", "hash")
    monkeypatch.setenv("ADMIN_USER_ID", "1")

    from app_paths import reset_data_dir_cache

    reset_data_dir_cache()
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        get_settings()
