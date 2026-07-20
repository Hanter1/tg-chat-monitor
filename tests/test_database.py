import pytest

import database as db
from config import Settings


@pytest.fixture
async def database():
    db.init_db("sqlite+aiosqlite:///:memory:")
    await db.create_tables()
    yield db


@pytest.mark.asyncio
async def test_add_and_get_chat(database):
    is_new = await db.add_chat(-100123, "Test", "testgroup", "supergroup")
    assert is_new is True

    chat = await db.get_chat(-100123)
    assert chat is not None
    assert chat.title == "Test"
    assert chat.is_active is True


@pytest.mark.asyncio
async def test_add_chat_updates_existing(database):
    await db.add_chat(-100123, "Old", None, "supergroup")
    is_new = await db.add_chat(-100123, "New", "newname", "supergroup")
    assert is_new is False

    chat = await db.get_chat(-100123)
    assert chat.title == "New"
    assert chat.username == "newname"


@pytest.mark.asyncio
async def test_keywords_crud(database):
    assert await db.add_keyword("bitcoin") is True
    assert await db.add_keyword("bitcoin") is False

    words = await db.get_all_keywords()
    assert len(words) == 1
    assert words[0] == "bitcoin"

    assert await db.remove_keyword("bitcoin") is True
    assert await db.get_all_keywords() == []


@pytest.mark.asyncio
async def test_toggle_chat_active(database):
    await db.add_chat(-100123, "Test", None, "supergroup")
    state = await db.toggle_chat_active(-100123)
    assert state is False

    chat = await db.get_chat(-100123)
    assert chat.is_active is False


@pytest.mark.asyncio
async def test_log_match_dedup(database):
    assert await db.log_match(
        chat_id=-100123,
        chat_title="Test",
        message_id=42,
        text_preview="hello",
        keywords="hello",
        message_link="https://t.me/c/1/42",
    ) is True
    assert await db.log_match(
        chat_id=-100123,
        chat_title="Test",
        message_id=42,
        text_preview="hello again",
        keywords="hello",
        message_link="https://t.me/c/1/42",
    ) is False

    records = await db.get_recent_matches()
    assert len(records) == 1
    assert records[0].message_id == 42


@pytest.mark.asyncio
async def test_bot_settings_from_env_defaults(database):
    defaults = Settings(
        bot_token="x",
        admin_user_id=1,
        api_id=1,
        api_hash="h",
        telethon_session="s",
        database_url="sqlite+aiosqlite:///:memory:",
        poll_interval=25,
        scan_history_limit=50,
        scan_period_days=14,
        scan_mode="search",
        telegram_notify=True,
        allow_no_bot=False,
    )
    await db.create_tables(env_defaults=defaults)
    settings = await db.get_bot_settings()
    assert settings.poll_interval == 25
    assert settings.scan_history_limit == 50
    assert settings.scan_period_days == 14
    assert settings.scan_mode == "search"
