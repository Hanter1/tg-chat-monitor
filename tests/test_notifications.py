import pytest

from notifications import MatchEvent, NotificationService


class FakeBot:
    def __init__(self):
        self.messages: list[dict] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append({"chat_id": chat_id, "text": text, **kwargs})


@pytest.mark.asyncio
async def test_instant_notification_sends_immediately(monkeypatch):
    bot = FakeBot()
    service = NotificationService(bot, admin_user_id=1)
    service._notify_mode = "instant"

    async def fake_log_match(**kwargs):
        return True

    monkeypatch.setattr("notifications.db.log_match", fake_log_match)

    event = MatchEvent(
        chat_id=-1001,
        chat_title="Chat",
        chat_type="supergroup",
        username=None,
        message_id=10,
        text="bitcoin news",
        matched_keywords=["bitcoin"],
        message_link="https://t.me/c/1/10",
    )
    await service.notify(event)
    assert len(bot.messages) == 1
    assert "bitcoin" in bot.messages[0]["text"]


@pytest.mark.asyncio
async def test_flush_digest_batches_pending(monkeypatch):
    bot = FakeBot()
    service = NotificationService(bot, admin_user_id=1)
    service._notify_mode = "digest_15"

    async def fake_log_match(**kwargs):
        return True

    monkeypatch.setattr("notifications.db.log_match", fake_log_match)

    for i in range(2):
        await service.notify(
            MatchEvent(
                chat_id=-1001,
                chat_title=f"Chat {i}",
                chat_type="supergroup",
                username=None,
                message_id=i,
                text=f"match {i}",
                matched_keywords=["kw"],
                message_link=f"https://t.me/c/1/{i}",
            )
        )

    assert len(bot.messages) == 0
    assert len(service._pending) == 2

    await service.flush_digest()
    assert len(bot.messages) == 1
    assert "Дайджест" in bot.messages[0]["text"]
    assert len(service._pending) == 0


@pytest.mark.asyncio
async def test_notify_skips_duplicate(monkeypatch):
    bot = FakeBot()
    service = NotificationService(bot, admin_user_id=1)
    service._notify_mode = "instant"

    async def fake_log_match(**kwargs):
        return False

    monkeypatch.setattr("notifications.db.log_match", fake_log_match)

    event = MatchEvent(
        chat_id=-1001,
        chat_title="Chat",
        chat_type="supergroup",
        username=None,
        message_id=10,
        text="bitcoin news",
        matched_keywords=["bitcoin"],
        message_link="https://t.me/c/1/10",
    )
    sent = await service.notify(event)
    assert sent is False
    assert len(bot.messages) == 0
