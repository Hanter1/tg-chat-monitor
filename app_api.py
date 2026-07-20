"""Синхронный API для Android UI поверх database / Telethon / monitor."""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import Future
from typing import Any

import database as db
from runtime_state import get_runtime_handle
from services.chat_resolver import resolve_chat_reference
from services.dialogs import fetch_dialogs_page
from services.scan_config import ScanConfig

logger = logging.getLogger(__name__)


class AppApiError(Exception):
    def __init__(self, message: str, *, code: str = "error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _require_handle():
    handle = get_runtime_handle()
    if handle is None:
        raise AppApiError("Runtime не готов", code="not_ready")
    return handle


def _run_coro(coro):
    """Выполнить coroutine в event loop runtime из другого потока."""
    from android_bridge import get_loop

    loop = get_loop()
    if loop is None or not loop.is_running():
        raise AppApiError("Event loop не запущен", code="not_ready")

    future: Future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=120)


def _chat_dict(chat) -> dict[str, Any]:
    return {
        "chat_id": chat.chat_id,
        "title": chat.title,
        "username": chat.username,
        "chat_type": chat.chat_type,
        "is_active": chat.is_active,
        "last_message_id": chat.last_message_id,
    }


def _match_dict(record) -> dict[str, Any]:
    return {
        "id": record.id,
        "chat_id": record.chat_id,
        "chat_title": record.chat_title,
        "message_id": record.message_id,
        "text_preview": record.text_preview,
        "keywords": record.keywords,
        "message_link": record.message_link,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _ok(data: Any = None) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def _err(exc: Exception) -> str:
    if isinstance(exc, AppApiError):
        return json.dumps(
            {"ok": False, "error": exc.message, "code": exc.code},
            ensure_ascii=False,
        )
    logger.exception("app_api error")
    return json.dumps(
        {"ok": False, "error": str(exc), "code": "error"},
        ensure_ascii=False,
    )


async def _dashboard_async() -> dict[str, Any]:
    handle = _require_handle()
    stats = await db.get_stats()
    bot_settings = await db.get_bot_settings()
    return {
        "runtime": "running",
        "monitor_running": handle.monitor.is_running,
        "scanning": handle.history_scanner.is_scanning,
        "admin_user_id": handle.admin_user_id,
        "bot_enabled": handle.bot is not None,
        "telegram_notify": bool(bot_settings.telegram_notify),
        "notify_mode": bot_settings.notify_mode,
        "poll_interval": bot_settings.poll_interval,
        "stats": stats,
    }


def get_dashboard() -> str:
    try:
        return _ok(_run_coro(_dashboard_async()))
    except Exception as exc:
        return _err(exc)


async def _list_chats_async() -> list[dict[str, Any]]:
    _require_handle()
    chats = await db.get_all_chats()
    return [_chat_dict(c) for c in chats]


def list_chats() -> str:
    try:
        return _ok(_run_coro(_list_chats_async()))
    except Exception as exc:
        return _err(exc)


async def _toggle_chat_async(chat_id: int) -> dict[str, Any]:
    _require_handle()
    active = await db.toggle_chat_active(chat_id)
    if active is None:
        raise AppApiError("Чат не найден", code="not_found")
    chat = await db.get_chat(chat_id)
    assert chat is not None
    return _chat_dict(chat)


def toggle_chat(chat_id: int) -> str:
    try:
        return _ok(_run_coro(_toggle_chat_async(int(chat_id))))
    except Exception as exc:
        return _err(exc)


async def _remove_chat_async(chat_id: int) -> dict[str, Any]:
    _require_handle()
    removed = await db.remove_chat(int(chat_id))
    if not removed:
        raise AppApiError("Чат не найден", code="not_found")
    return {"removed": True, "chat_id": int(chat_id)}


def remove_chat(chat_id: int) -> str:
    try:
        return _ok(_run_coro(_remove_chat_async(int(chat_id))))
    except Exception as exc:
        return _err(exc)


async def _list_dialogs_async(page: int) -> dict[str, Any]:
    handle = _require_handle()
    items, total = await fetch_dialogs_page(handle.telethon, int(page))
    monitored = {c.chat_id for c in await db.get_all_chats()}
    for item in items:
        item["monitored"] = item["chat_id"] in monitored
    return {"items": items, "total": total, "page": int(page)}


def list_dialogs(page: int = 0) -> str:
    try:
        return _ok(_run_coro(_list_dialogs_async(int(page))))
    except Exception as exc:
        return _err(exc)


async def _add_chat_async(chat_id: int) -> dict[str, Any]:
    handle = _require_handle()
    ref = await resolve_chat_reference(str(int(chat_id)), handle.telethon)
    if ref is None:
        raise AppApiError("Не удалось добавить чат", code="resolve_failed")
    is_new = await db.add_chat(
        chat_id=ref.chat_id,
        title=ref.title,
        username=ref.username,
        chat_type=ref.chat_type,
    )
    chat = await db.get_chat(ref.chat_id)
    assert chat is not None
    return {"is_new": is_new, "chat": _chat_dict(chat)}


def add_chat(chat_id: int) -> str:
    try:
        return _ok(_run_coro(_add_chat_async(int(chat_id))))
    except Exception as exc:
        return _err(exc)


async def _add_chat_ref_async(ref: str) -> dict[str, Any]:
    handle = _require_handle()
    chat_ref = await resolve_chat_reference(ref, handle.telethon)
    if chat_ref is None:
        raise AppApiError("Чат не найден", code="resolve_failed")
    is_new = await db.add_chat(
        chat_id=chat_ref.chat_id,
        title=chat_ref.title,
        username=chat_ref.username,
        chat_type=chat_ref.chat_type,
    )
    chat = await db.get_chat(chat_ref.chat_id)
    assert chat is not None
    return {"is_new": is_new, "chat": _chat_dict(chat)}


def add_chat_ref(ref: str) -> str:
    try:
        return _ok(_run_coro(_add_chat_ref_async(str(ref))))
    except Exception as exc:
        return _err(exc)


async def _list_words_async() -> list[str]:
    _require_handle()
    return await db.get_all_keywords()


def list_words() -> str:
    try:
        return _ok(_run_coro(_list_words_async()))
    except Exception as exc:
        return _err(exc)


async def _add_word_async(word: str) -> dict[str, Any]:
    _require_handle()
    added = await db.add_keyword(word)
    words = await db.get_all_keywords()
    return {"added": added, "words": words}


def add_word(word: str) -> str:
    try:
        return _ok(_run_coro(_add_word_async(str(word))))
    except Exception as exc:
        return _err(exc)


async def _remove_word_async(word: str) -> dict[str, Any]:
    _require_handle()
    removed = await db.remove_keyword(word)
    if not removed:
        raise AppApiError("Слово не найдено", code="not_found")
    return {"removed": True, "words": await db.get_all_keywords()}


def remove_word(word: str) -> str:
    try:
        return _ok(_run_coro(_remove_word_async(str(word))))
    except Exception as exc:
        return _err(exc)


async def _start_monitor_async() -> dict[str, Any]:
    handle = _require_handle()
    chats = await db.get_active_chats()
    words = await db.get_all_keywords()
    if not chats:
        raise AppApiError("Добавьте хотя бы один чат", code="no_chats")
    if not words:
        raise AppApiError("Добавьте ключевые слова", code="no_words")
    started = await handle.monitor.start()
    return {"started": started, "monitor_running": handle.monitor.is_running}


def start_monitor() -> str:
    try:
        return _ok(_run_coro(_start_monitor_async()))
    except Exception as exc:
        return _err(exc)


async def _stop_monitor_async() -> dict[str, Any]:
    handle = _require_handle()
    await handle.monitor.stop()
    return {"monitor_running": handle.monitor.is_running}


def stop_monitor() -> str:
    try:
        return _ok(_run_coro(_stop_monitor_async()))
    except Exception as exc:
        return _err(exc)


async def _list_matches_async(limit: int) -> list[dict[str, Any]]:
    _require_handle()
    records = await db.get_recent_matches(limit=int(limit))
    return [_match_dict(r) for r in records]


def list_matches(limit: int = 50) -> str:
    try:
        return _ok(_run_coro(_list_matches_async(int(limit))))
    except Exception as exc:
        return _err(exc)


async def _get_settings_async() -> dict[str, Any]:
    handle = _require_handle()
    bot_settings = await db.get_bot_settings()
    return {
        "notify_mode": bot_settings.notify_mode,
        "poll_interval": bot_settings.poll_interval,
        "scan_history_limit": bot_settings.scan_history_limit,
        "scan_period_days": bot_settings.scan_period_days,
        "scan_mode": bot_settings.scan_mode,
        "telegram_notify": bool(bot_settings.telegram_notify),
        "bot_enabled": handle.bot is not None,
        "admin_user_id": handle.admin_user_id,
    }


def get_app_settings() -> str:
    try:
        return _ok(_run_coro(_get_settings_async()))
    except Exception as exc:
        return _err(exc)


async def _update_settings_async(payload: dict[str, Any]) -> dict[str, Any]:
    handle = _require_handle()
    allowed = {
        "notify_mode",
        "poll_interval",
        "scan_history_limit",
        "scan_period_days",
        "scan_mode",
        "telegram_notify",
    }
    updates = {k: v for k, v in payload.items() if k in allowed}
    if "poll_interval" in updates:
        updates["poll_interval"] = max(5, int(updates["poll_interval"]))
    if "scan_history_limit" in updates:
        updates["scan_history_limit"] = max(1, int(updates["scan_history_limit"]))
    if "scan_period_days" in updates:
        updates["scan_period_days"] = int(updates["scan_period_days"])
    if "telegram_notify" in updates:
        updates["telegram_notify"] = bool(updates["telegram_notify"])
    if updates:
        await db.update_bot_settings(**updates)
        await handle.notifier.refresh_settings()
    return await _get_settings_async()


def update_app_settings(json_payload: str) -> str:
    try:
        payload = json.loads(json_payload) if json_payload else {}
        if not isinstance(payload, dict):
            raise AppApiError("Некорректный JSON", code="bad_request")
        return _ok(_run_coro(_update_settings_async(payload)))
    except Exception as exc:
        return _err(exc)


async def _start_scan_async(chat_id: int | None) -> dict[str, Any]:
    handle = _require_handle()
    if handle.history_scanner.is_scanning:
        raise AppApiError("Сканирование уже идёт", code="busy")
    config = ScanConfig.from_bot_settings(await db.get_bot_settings())
    result = await handle.history_scanner.scan(
        chat_id=int(chat_id) if chat_id else None,
        config=config,
        progress_message=None,
    )
    return {
        "chats_scanned": result.chats_scanned,
        "matches_found": result.matches_found,
        "matches_sent": result.matches_sent,
        "matches_skipped": result.matches_skipped,
    }


def start_scan(chat_id: int = 0) -> str:
    try:
        cid = int(chat_id) if chat_id else None
        return _ok(_run_coro(_start_scan_async(cid)))
    except Exception as exc:
        return _err(exc)


def scan_status() -> str:
    try:
        handle = _require_handle()
        return _ok({"scanning": handle.history_scanner.is_scanning})
    except Exception as exc:
        return _err(exc)
