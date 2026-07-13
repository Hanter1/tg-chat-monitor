import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from monitor import ChatMonitor


@pytest.mark.asyncio
async def test_backup_poll_keeps_running_after_error(monkeypatch):
    sleep_delays: list[float] = []
    catch_up_calls = 0

    async def fake_sleep(seconds: float) -> None:
        sleep_delays.append(seconds)
        if len(sleep_delays) >= 4:
            monitor._running = False

    async def fake_catch_up() -> None:
        nonlocal catch_up_calls
        catch_up_calls += 1
        if catch_up_calls == 1:
            raise RuntimeError("temporary network error")

    async def fake_get_bot_settings():
        return SimpleNamespace(poll_interval=5)

    async def fake_set_monitor_running(_: bool) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr("monitor.db.get_bot_settings", fake_get_bot_settings)
    monkeypatch.setattr("monitor.db.set_monitor_running", fake_set_monitor_running)

    settings = SimpleNamespace(poll_interval=5)
    monitor = ChatMonitor(
        settings=settings,
        telethon_client=MagicMock(),
        bot=MagicMock(),
        notifier=AsyncMock(),
    )
    monitor._running = True
    monitor._catch_up_all_chats = fake_catch_up

    await monitor._backup_poll_loop()

    assert catch_up_calls >= 2
    assert any(delay == 5 for delay in sleep_delays)
