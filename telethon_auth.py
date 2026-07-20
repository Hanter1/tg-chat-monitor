"""Авторизация Telethon с подключаемыми источниками ввода (CLI / Android UI)."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import Awaitable, Callable
from typing import Protocol

from telethon import TelegramClient

logger = logging.getLogger(__name__)

PromptFn = Callable[[], Awaitable[str] | str]


class AuthPrompter(Protocol):
    async def request_phone(self) -> str: ...

    async def request_code(self) -> str: ...

    async def request_password(self) -> str: ...


class ConsoleAuthPrompter:
    """Запросы через stdin (ПК / терминал)."""

    async def request_phone(self) -> str:
        return await _prompt(
            "Введите номер телефона Telethon (международный формат, +7...): "
        )

    async def request_code(self) -> str:
        return await _prompt("Введите код из Telegram: ")

    async def request_password(self) -> str:
        return await _prompt("Введите пароль двухфакторной аутентификации: ")


class CallableAuthPrompter:
    """Prompter из трёх колбэков (удобно для Android bridge)."""

    def __init__(
        self,
        request_phone: PromptFn,
        request_code: PromptFn,
        request_password: PromptFn,
    ) -> None:
        self._request_phone = request_phone
        self._request_code = request_code
        self._request_password = request_password

    async def request_phone(self) -> str:
        return await _call_prompt(self._request_phone)

    async def request_code(self) -> str:
        return await _call_prompt(self._request_code)

    async def request_password(self) -> str:
        return await _call_prompt(self._request_password)


async def _prompt(message: str) -> str:
    return await asyncio.to_thread(lambda: input(message).strip())


async def _call_prompt(fn: PromptFn) -> str:
    if asyncio.iscoroutinefunction(fn):
        result = await fn()
    else:
        result = fn()
        if isinstance(result, Awaitable):
            result = await result
    text = str(result or "").strip()
    if not text:
        raise ValueError("Пустой ответ при авторизации Telethon")
    return text


async def connect_with_retry(client: TelegramClient, attempts: int = 5) -> None:
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            await client.connect()
            return
        except sqlite3.OperationalError as exc:
            last_error = exc
            if "locked" not in str(exc).lower() or attempt == attempts - 1:
                raise
            wait_seconds = 2 * (attempt + 1)
            logger.warning(
                "Файл сессии Telethon занят, повтор через %s сек... (%s/%s)",
                wait_seconds,
                attempt + 1,
                attempts,
            )
            await asyncio.sleep(wait_seconds)

    if last_error:
        raise last_error


async def ensure_telethon_authorized(
    client: TelegramClient,
    prompter: AuthPrompter | None = None,
) -> None:
    await connect_with_retry(client)

    if await client.is_user_authorized():
        logger.info("Telethon-сессия авторизована")
        return

    auth = prompter or ConsoleAuthPrompter()
    phone = await auth.request_phone()
    await client.send_code_request(phone)
    code = await auth.request_code()

    try:
        await client.sign_in(phone, code)
    except Exception:
        password = await auth.request_password()
        await client.sign_in(password=password)

    logger.info("Telethon авторизация успешна")
