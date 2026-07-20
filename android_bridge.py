"""Точка входа Python для Android (Chaquopy)."""

from __future__ import annotations

import asyncio
import json
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
_notification_broker: Any = None


def configure(
    data_dir: str,
    auth_broker: Any = None,
    notification_broker: Any = None,
) -> str:
    """Вызвать из Kotlin до start(): каталог данных и брокеры."""
    global _auth_broker, _notification_broker
    os.environ["TG_MONITOR_DATA_DIR"] = data_dir
    os.environ["TG_MONITOR_SKIP_LOCK"] = "1"
    os.environ["TG_MONITOR_ALLOW_NO_BOT"] = "1"
    os.environ["HOME"] = data_dir

    from app_paths import reset_data_dir_cache, set_data_dir

    reset_data_dir_cache()
    set_data_dir(data_dir)
    _auth_broker = auth_broker
    if notification_broker is not None:
        _notification_broker = notification_broker
    return data_dir


def set_notification_broker(broker: Any) -> None:
    global _notification_broker
    _notification_broker = broker


def get_loop() -> asyncio.AbstractEventLoop | None:
    return _loop


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


def _emit_match_to_android(event) -> None:
    broker = _notification_broker
    if broker is None:
        return
    try:
        payload = json.dumps(event.to_dict(), ensure_ascii=False)
        broker.onMatch(payload)
    except Exception:
        logger.exception("Failed to deliver match to Android")


async def _match_sink(event) -> None:
    await asyncio.to_thread(_emit_match_to_android, event)


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
        match_sink=_match_sink,
    )


# --- App API re-exports for Kotlin ---

def get_dashboard() -> str:
    from app_api import get_dashboard as _fn

    return _fn()


def list_chats() -> str:
    from app_api import list_chats as _fn

    return _fn()


def toggle_chat(chat_id: int) -> str:
    from app_api import toggle_chat as _fn

    return _fn(chat_id)


def remove_chat(chat_id: int) -> str:
    from app_api import remove_chat as _fn

    return _fn(chat_id)


def list_dialogs(page: int = 0) -> str:
    from app_api import list_dialogs as _fn

    return _fn(page)


def add_chat(chat_id: int) -> str:
    from app_api import add_chat as _fn

    return _fn(chat_id)


def add_chat_ref(ref: str) -> str:
    from app_api import add_chat_ref as _fn

    return _fn(ref)


def list_words() -> str:
    from app_api import list_words as _fn

    return _fn()


def add_word(word: str) -> str:
    from app_api import add_word as _fn

    return _fn(word)


def remove_word(word: str) -> str:
    from app_api import remove_word as _fn

    return _fn(word)


def start_monitor() -> str:
    from app_api import start_monitor as _fn

    return _fn()


def stop_monitor() -> str:
    from app_api import stop_monitor as _fn

    return _fn()


def list_matches(limit: int = 50) -> str:
    from app_api import list_matches as _fn

    return _fn(limit)


def get_app_settings() -> str:
    from app_api import get_app_settings as _fn

    return _fn()


def update_app_settings(json_payload: str) -> str:
    from app_api import update_app_settings as _fn

    return _fn(json_payload)


def start_scan(chat_id: int = 0) -> str:
    from app_api import start_scan as _fn

    return _fn(chat_id)


def scan_status() -> str:
    from app_api import scan_status as _fn

    return _fn()
