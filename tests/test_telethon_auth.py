"""Тесты auth prompter."""

from __future__ import annotations

import pytest

from telethon_auth import CallableAuthPrompter


@pytest.mark.asyncio
async def test_callable_auth_prompter():
    prompter = CallableAuthPrompter(
        request_phone=lambda: "+79001112233",
        request_code=lambda: "12345",
        request_password=lambda: "secret",
    )
    assert await prompter.request_phone() == "+79001112233"
    assert await prompter.request_code() == "12345"
    assert await prompter.request_password() == "secret"


@pytest.mark.asyncio
async def test_callable_auth_prompter_rejects_empty():
    prompter = CallableAuthPrompter(
        request_phone=lambda: "  ",
        request_code=lambda: "1",
        request_password=lambda: "1",
    )
    with pytest.raises(ValueError, match="Пустой"):
        await prompter.request_phone()
