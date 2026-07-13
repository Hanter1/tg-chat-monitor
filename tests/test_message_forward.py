from unittest.mock import AsyncMock, MagicMock

import pytest

from bot_ui import open_message_callback
from services.message_forward import format_forward_header, forward_message_to_bot


def test_open_message_callback_format():
    assert open_message_callback(-1001234567890, 42) == "open:-1001234567890:42"
    assert len(open_message_callback(-1001234567890, 42)) <= 64


def test_format_forward_header_includes_chat_title():
    text = format_forward_header("Test Group", chat_type="supergroup", keywords=["bitcoin"])
    assert "Test Group" in text
    assert "bitcoin" in text
    assert "Пересылка из чата" in text


@pytest.mark.asyncio
async def test_forward_message_to_bot_sends_header():
    telethon = MagicMock()
    telethon.get_entity = AsyncMock(return_value="bot_peer")
    telethon.send_message = AsyncMock()
    telethon.forward_messages = AsyncMock()

    ok = await forward_message_to_bot(
        telethon,
        "testbot",
        -1001,
        99,
        chat_title="My Chat",
        chat_type="supergroup",
    )

    assert ok is True
    telethon.get_entity.assert_awaited_once_with("testbot")
    telethon.send_message.assert_awaited_once()
    telethon.forward_messages.assert_awaited_once_with("bot_peer", 99, from_peer=-1001)


@pytest.mark.asyncio
async def test_forward_message_to_bot_without_title():
    telethon = MagicMock()
    telethon.get_entity = AsyncMock(return_value="bot_peer")
    telethon.send_message = AsyncMock()
    telethon.forward_messages = AsyncMock()

    ok = await forward_message_to_bot(telethon, "testbot", -1001, 99)

    assert ok is True
    telethon.send_message.assert_not_awaited()
    telethon.forward_messages.assert_awaited_once_with("bot_peer", 99, from_peer=-1001)
