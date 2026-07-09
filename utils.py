def build_message_link(chat_id: int, message_id: int, username: str | None) -> str:
    """
    Публичный чат:  https://t.me/username/message_id
    Приватная супергруппа: https://t.me/c/internal_id/message_id
      internal_id — chat_id без префикса -100 (например -1001234567890 → 1234567890)
    """
    if username:
        return f"https://t.me/{username}/{message_id}"

    internal_id = _private_chat_link_id(chat_id)
    return f"https://t.me/c/{internal_id}/{message_id}"


def _private_chat_link_id(chat_id: int) -> int:
    chat_id_str = str(chat_id)
    if chat_id_str.startswith("-100"):
        return int(chat_id_str[4:])
    return abs(chat_id)


def message_contains_keyword(text: str, keywords: list[str]) -> bool:
    if not text or not keywords:
        return False
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in keywords)
