import pytest
from telethon.tl.types import Channel, User

from services.chat_resolver import ChatRef, entity_to_chat_ref


def test_entity_to_chat_ref_user():
    user = User(id=42, is_self=False, contact=False, mutual_contact=False, deleted=False, bot=False, bot_chat_history=False, bot_nochats=False, verified=False, restricted=False, min=False, bot_inline_geo=False, support=False, scam=False, fake=False, bot_attach_menu=False, premium=False, attach_menu_enabled=False, bot_can_edit=False, close_friend=False, stories_hidden=False, stories_unavailable=True, access_hash=0, first_name="John", last_name="Doe", username="johndoe", phone=None, photo=None, status=None, bot_info_version=None, restriction_reason=None, bot_inline_placeholder=None, lang_code=None, emoji_status=None, usernames=None, stories_max_id=None, color=None, profile_color=None, bot_active_users=None, bot_verification_icon=None, send_paid_messages_stars=None)
    ref = entity_to_chat_ref(user)
    assert ref == ChatRef(42, "John Doe", "johndoe", "private")


def test_entity_to_chat_ref_channel():
    channel = Channel(
        id=1234567890,
        title="Test Channel",
        photo=None,
        date=None,
        creator=False,
        left=False,
        broadcast=True,
        verified=False,
        megagroup=False,
        restricted=False,
        signatures=False,
        min=False,
        scam=False,
        has_link=False,
        has_geo=False,
        slowmode_enabled=False,
        call_active=False,
        call_not_empty=False,
        fake=False,
        gigagroup=False,
        noforwards=False,
        join_to_send=False,
        join_request=False,
        forum=False,
        stories_hidden=False,
        stories_hidden_min=False,
        stories_unavailable=True,
        access_hash=0,
        username="testchannel",
        restriction_reason=None,
        admin_rights=None,
        banned_rights=None,
        default_banned_rights=None,
        participants_count=None,
        usernames=None,
        stories_max_id=None,
        color=None,
        profile_color=None,
        emoji_status=None,
        level=None,
        subscription_until_date=None,
        bot_verification_icon=None,
        send_paid_messages_stars=None,
    )
    ref = entity_to_chat_ref(channel)
    assert ref.chat_id == -1001234567890
    assert ref.title == "Test Channel"
    assert ref.chat_type == "channel"


def test_entity_to_chat_ref_supergroup():
    group = Channel(
        id=9876543210,
        title="Test Group",
        photo=None,
        date=None,
        creator=False,
        left=False,
        broadcast=False,
        verified=False,
        megagroup=True,
        restricted=False,
        signatures=False,
        min=False,
        scam=False,
        has_link=False,
        has_geo=False,
        slowmode_enabled=False,
        call_active=False,
        call_not_empty=False,
        fake=False,
        gigagroup=False,
        noforwards=False,
        join_to_send=False,
        join_request=False,
        forum=False,
        stories_hidden=False,
        stories_hidden_min=False,
        stories_unavailable=True,
        access_hash=0,
        username=None,
        restriction_reason=None,
        admin_rights=None,
        banned_rights=None,
        default_banned_rights=None,
        participants_count=None,
        usernames=None,
        stories_max_id=None,
        color=None,
        profile_color=None,
        emoji_status=None,
        level=None,
        subscription_until_date=None,
        bot_verification_icon=None,
        send_paid_messages_stars=None,
    )
    ref = entity_to_chat_ref(group)
    assert ref.chat_type == "supergroup"


@pytest.mark.asyncio
async def test_resolve_chat_reference_numeric_fallback(monkeypatch):
    from services import chat_resolver

    async def fail_get_entity(_):
        raise ValueError("not found")

    ref = await chat_resolver.resolve_chat_reference(
        "-100111",
        telethon=type("T", (), {"get_entity": fail_get_entity})(),
    )
    assert ref is not None
    assert ref.chat_id == -100111
    assert ref.chat_type == "supergroup"
