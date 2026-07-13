import logging
from html import escape

from telethon import TelegramClient

logger = logging.getLogger(__name__)

CHAT_TYPE_ICONS = {
    "private": "👤",
    "group": "👥",
    "supergroup": "👥",
    "channel": "📢",
}


def format_forward_header(
    chat_title: str,
    *,
    chat_type: str = "unknown",
    keywords: list[str] | None = None,
) -> str:
    icon = CHAT_TYPE_ICONS.get(chat_type, "💬")
    safe_title = escape(chat_title.strip() or "Без названия")
    lines = [
        "📎 <b>Пересылка из чата</b>",
        "",
        f"{icon} <b>{safe_title}</b>",
    ]
    if keywords:
        words = " · ".join(f"<code>{escape(word)}</code>" for word in keywords)
        lines.extend(["", f"🔑 {words}"])
    return "\n".join(lines)


async def forward_message_to_bot(
    telethon: TelegramClient,
    bot_username: str,
    chat_id: int,
    message_id: int,
    *,
    chat_title: str | None = None,
    chat_type: str = "unknown",
    keywords: list[str] | None = None,
) -> bool:
    """Пересылает сообщение в ЛС с ботом — перед пересылкой показывает источник."""
    try:
        bot_peer = await telethon.get_entity(bot_username)
        if chat_title:
            await telethon.send_message(
                bot_peer,
                format_forward_header(chat_title, chat_type=chat_type, keywords=keywords),
                parse_mode="html",
            )
        await telethon.forward_messages(bot_peer, message_id, from_peer=chat_id)
        return True
    except Exception:
        logger.exception(
            "Не удалось переслать сообщение chat_id=%s msg_id=%s",
            chat_id,
            message_id,
        )
        return False
