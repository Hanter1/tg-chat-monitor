import logging
import re

logger = logging.getLogger(__name__)

_TME_C_LINK = re.compile(r"https?://t\.me/c/(\d+)(?:/(\d+))?(?:/(\d+))?")


def build_message_link(
    chat_id: int,
    message_id: int,
    username: str | None,
    *,
    topic_id: int | None = None,
) -> str:
    """
    Публичный чат:  https://t.me/username/message_id
    Приватная супергруппа: https://t.me/c/internal_id/message_id
    Форум-топик: https://t.me/c/internal_id/topic_id/message_id
    """
    if chat_id > 0:
        return f"tg://openmessage?chat_id={chat_id}&message_id={message_id}"

    if username:
        return f"https://t.me/{username}/{message_id}"

    internal_id = _private_chat_link_id(chat_id)
    if topic_id:
        return f"https://t.me/c/{internal_id}/{topic_id}/{message_id}"
    return f"https://t.me/c/{internal_id}/{message_id}"


def build_app_message_link(
    chat_id: int,
    message_id: int,
    *,
    username: str | None = None,
    topic_id: int | None = None,
) -> str:
    """Ссылка для inline-кнопок бота — открывается в приложении Telegram."""
    if username:
        return f"https://t.me/{username}/{message_id}"

    if topic_id and chat_id < 0:
        internal_id = _private_chat_link_id(chat_id)
        return f"https://t.me/c/{internal_id}/{topic_id}/{message_id}"

    if chat_id < 0:
        return f"tg://openmessage?chat_id={chat_id}&message_id={message_id}"

    return f"tg://openmessage?chat_id={chat_id}&message_id={message_id}"


def normalize_message_link_for_button(
    link: str,
    *,
    chat_id: int | None = None,
    message_id: int | None = None,
    username: str | None = None,
) -> str:
    """Конвертирует t.me/c ссылки в tg:// для кнопок бота."""
    if not link:
        if chat_id is not None and message_id is not None:
            return build_app_message_link(chat_id, message_id, username=username)
        return link

    if link.startswith("tg://"):
        return link

    match = _TME_C_LINK.match(link)
    if match:
        internal_id, part1, part2 = match.group(1), match.group(2), match.group(3)
        if part2:
            return link
        if chat_id is not None:
            return f"tg://openmessage?chat_id={chat_id}&message_id={part1}"
        return f"tg://privatepost?channel={internal_id}&post={part1}"

    if link.startswith("https://t.me/") and chat_id is not None and message_id is not None and chat_id < 0:
        return build_app_message_link(chat_id, message_id, username=username)

    return link


def _extract_topic_id(message) -> int | None:
    reply_to = getattr(message, "reply_to", None)
    if reply_to is None:
        return None
    topic_id = getattr(reply_to, "reply_to_top_id", None)
    return topic_id or None


async def get_message_link(client, chat_id: int, message_id: int, username: str | None, *, message=None) -> str:
    """Возвращает рабочую ссылку на сообщение для кнопок бота."""
    from telethon.tl.types import Channel, User

    topic_id = _extract_topic_id(message) if message is not None else None
    entity = None

    try:
        entity = await client.get_entity(chat_id)
    except Exception:
        logger.debug("get_entity не сработал для chat_id=%s", chat_id, exc_info=True)

    entity_username = username or getattr(entity, "username", None)
    if entity_username and not isinstance(entity, User):
        return build_app_message_link(chat_id, message_id, username=entity_username, topic_id=topic_id)

    if isinstance(entity, Channel) and entity.broadcast and entity_username:
        return f"https://t.me/{entity_username}/{message_id}"

    return build_app_message_link(chat_id, message_id, topic_id=topic_id)


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


def find_matched_keywords(text: str, keywords: list[str]) -> list[str]:
    if not text or not keywords:
        return []
    lower_text = text.lower()
    return [keyword for keyword in keywords if keyword in lower_text]


def infer_chat_type_from_id(chat_id: int) -> str:
    if chat_id > 0:
        return "private"
    return "supergroup"


def detect_entity_chat_type(entity) -> str:
    from telethon.tl.types import Channel, Chat, User

    if isinstance(entity, User):
        return "private"
    if isinstance(entity, Channel):
        return "channel" if entity.broadcast else "supergroup"
    if isinstance(entity, Chat):
        return "group"
    if hasattr(entity, "id"):
        return infer_chat_type_from_id(entity.id)
    return "unknown"
