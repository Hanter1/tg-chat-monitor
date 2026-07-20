"""Точка входа Python для Android (Chaquopy)."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_status = "idle"
_last_error = ""
_auth_broker: Any = None


def configure(data_dir: str, auth_broker: Any = None) -> str:
    """Вызвать из Kotlin до start(): каталог данных и брокер авторизации."""
    global _auth_broker
    os.environ["TG_MONITOR_DATA_DIR"] = data_dir
    os.environ["TG_MONITOR_SKIP_LOCK"] = "1"
    os.environ["HOME"] = data_dir

    from app_paths import reset_data_dir_cache, set_data_dir

    reset_data_dir_cache()
    set_data_dir(data_dir)
    _auth_broker = auth_broker
    return data_dir


def get_status() -> str:
    return _status


def get_last_error() -> str:
    return _last_error


def is_running() -> bool:
    return _status in {"starting", "running", "authorizing"}


def start() -> bool:
    """Запуск run_app в фоне. True если поток стартовал."""
    global _thread, _status, _last_error

    if is_running():
        return False

    _last_error = ""
    _status = "starting"

    def _runner() -> None:
        global _loop, _status, _last_error
        try:
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
            _loop.run_until_complete(_run())
        except Exception as exc:
            logger.exception("Android runtime failed")
            _last_error = str(exc)
            _status = "error"
        finally:
            if _loop is not None:
                try:
                    _loop.close()
                except Exception:
                    pass
                _loop = None
            if _status != "error":
                _status = "stopped"

    _thread = threading.Thread(target=_runner, name="tg-monitor-runtime", daemon=True)
    _thread.start()
    return True


def stop() -> None:
    """Остановить polling (мягко через остановку event loop tasks)."""
    global _status
    loop = _loop
    if loop is None or not loop.is_running():
        _status = "stopped"
        return

    def _cancel() -> None:
        for task in asyncio.all_tasks(loop):
            task.cancel()

    loop.call_soon_threadsafe(_cancel)


async def _run() -> None:
    global _status
    from config import get_settings
    from runtime import run_app
    from telethon_auth import CallableAuthPrompter

    settings = get_settings()
    prompter = None
    if _auth_broker is not None:
        broker = _auth_broker

        async def _phone() -> str:
            return await asyncio.to_thread(broker.requestPhone)

        async def _code() -> str:
            return await asyncio.to_thread(broker.requestCode)

        async def _password() -> str:
            return await asyncio.to_thread(broker.requestPassword)

        prompter = CallableAuthPrompter(
            request_phone=_phone,
            request_code=_code,
            request_password=_password,
        )
        _status = "authorizing"

    async def _on_ready() -> None:
        global _status
        _status = "running"

    await run_app(
        settings=settings,
        auth_prompter=prompter,
        on_ready=_on_ready,
    )
