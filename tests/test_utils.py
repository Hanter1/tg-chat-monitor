from utils import (
    _private_chat_link_id,
    build_app_message_link,
    build_message_link,
    detect_entity_chat_type,
    find_matched_keywords,
    infer_chat_type_from_id,
    message_contains_keyword,
    normalize_message_link_for_button,
)


def test_find_matched_keywords_case_insensitive():
    keywords = ["bitcoin", "eth"]
    assert find_matched_keywords("Buy BITCOIN now", keywords) == ["bitcoin"]
    assert find_matched_keywords("no match here", keywords) == []


def test_message_contains_keyword():
    assert message_contains_keyword("hello world", ["world"])
    assert not message_contains_keyword("", ["world"])
    assert not message_contains_keyword("hello", [])


def test_private_chat_link_id():
    assert _private_chat_link_id(-1001234567890) == 1234567890
    assert _private_chat_link_id(-12345) == 12345


def test_build_message_link_public_username():
    link = build_message_link(-100123, 42, "mygroup")
    assert link == "https://t.me/mygroup/42"


def test_build_message_link_private_supergroup():
    link = build_message_link(-1001234567890, 99, None)
    assert link == "https://t.me/c/1234567890/99"


def test_build_message_link_forum_topic():
    link = build_message_link(-1001234567890, 99, None, topic_id=5)
    assert link == "https://t.me/c/1234567890/5/99"


def test_build_message_link_private_user():
    link = build_message_link(12345, 1, None)
    assert link == "tg://openmessage?chat_id=12345&message_id=1"


def test_build_app_message_link_private_supergroup():
    link = build_app_message_link(-1001234567890, 99)
    assert link == "tg://openmessage?chat_id=-1001234567890&message_id=99"


def test_build_app_message_link_public_username():
    link = build_app_message_link(-100123, 42, username="mygroup")
    assert link == "https://t.me/mygroup/42"


def test_normalize_private_tme_c_link():
    link = normalize_message_link_for_button(
        "https://t.me/c/1234567890/99",
        chat_id=-1001234567890,
        message_id=99,
    )
    assert link == "tg://openmessage?chat_id=-1001234567890&message_id=99"


def test_normalize_keeps_forum_link():
    link = "https://t.me/c/1234567890/5/99"
    assert normalize_message_link_for_button(link) == link


def test_normalize_keeps_tg_link():
    link = "tg://openmessage?chat_id=-1001&message_id=2"
    assert normalize_message_link_for_button(link) == link


def test_infer_chat_type_from_id():
    assert infer_chat_type_from_id(123) == "private"
    assert infer_chat_type_from_id(-100123) == "supergroup"


def test_detect_entity_chat_type_user():
    class FakeUser:
        id = 1

    assert detect_entity_chat_type(FakeUser()) == "private"
