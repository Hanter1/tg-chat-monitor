import logging
import re
from dataclasses import dataclass

from aiogram.types import (
    Message,
    MessageOriginChannel,
    MessageOriginChat,
    MessageOriginHiddenUser,
    MessageOriginUser,
)
from telethon import TelegramClient
from telethon.tl.types import User
from telethon.utils import get_peer_id

import bot_ui as ui
import database as db
from utils import detect_entity_chat_type, infer_chat_type_from_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatRef:
    chat_id: int
    title: str
    username: str | None = None
    chat_type: str = "unknown"


def chat_from_aiogram_chat(chat) -> ChatRef:
    chat_type = chat.type.value if hasattr(chat.type, "value") else str(chat.type)
    return ChatRef(
        chat_id=chat.id,
        title=chat.title or str(chat.id),
        username=chat.username,
        chat_type=chat_type,
    )


def extract_forwarded_chat(message: Message) -> ChatRef | None:
    if message.forward_from_chat:
        return chat_from_aiogram_chat(message.forward_from_chat)

    origin = message.forward_origin
    if origin is None:
        return None

    if isinstance(origin, MessageOriginChannel):
        chat = origin.chat
        return ChatRef(chat.id, chat.title or str(chat.id), chat.username, "channel")

    if isinstance(origin, MessageOriginChat):
        chat = origin.sender_chat
        chat_type = chat.type.value if hasattr(chat.type, "value") else "supergroup"
        return ChatRef(chat.id, chat.title or str(chat.id), chat.username, chat_type)

    if isinstance(origin, MessageOriginUser):
        user = origin.sender_user
        title = user.full_name or user.username or str(user.id)
        return ChatRef(user.id, title, user.username, "private")

    return None


def forward_failure_hint(message: Message) -> str:
    origin = message.forward_origin

    if isinstance(origin, MessageOriginHiddenUser):
        return (
            "🔒 <b>Скрытая пересылка</b>\n\n"
            "Отправитель скрыл аккаунт.\n"
            "Используйте «📡 Мои группы» или <code>/add_chat @username</code>"
        )

    return (
        "❓ <b>Не удалось определить чат</b>\n\n"
        "Попробуйте:\n"
        "• «📡 Мои группы» в меню\n"
        "• Ответить <code>/add_chat</code> на пересылку\n"
        "• <code>/add_chat @username</code>"
    )


def entity_to_chat_ref(entity) -> ChatRef:
    chat_type = detect_entity_chat_type(entity)
    if isinstance(entity, User):
        title = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
        title = title or entity.username or str(entity.id)
        return ChatRef(entity.id, title, entity.username, chat_type)

    title = getattr(entity, "title", None) or str(entity.id)
    username = getattr(entity, "username", None)
    return ChatRef(get_peer_id(entity), title, username, chat_type)


async def resolve_chat_reference(ref: str, telethon: TelegramClient) -> ChatRef | None:
    ref = ref.strip()
    if not ref:
        return None

    link_match = re.search(r"(?:https?://)?t\.me/(?:c/)?([^/\s]+)", ref)
    if link_match:
        ref = link_match.group(1)

    if ref.startswith("@"):
        ref = ref[1:]

    if ref.lstrip("-").isdigit():
        chat_id = int(ref)
        try:
            entity = await telethon.get_entity(chat_id)
            return entity_to_chat_ref(entity)
        except Exception:
            logger.exception("Не удалось получить чат по ID %s", chat_id)
            return ChatRef(chat_id, str(chat_id), None, infer_chat_type_from_id(chat_id))

    try:
        entity = await telethon.get_entity(ref)
        return entity_to_chat_ref(entity)
    except Exception:
        logger.exception("Не удалось получить чат по ссылке/username: %s", ref)
        return None


async def save_chat(message: Message, chat_ref: ChatRef, *, edit: Message | None = None) -> None:
    is_new = await db.add_chat(
        chat_id=chat_ref.chat_id,
        title=chat_ref.title,
        username=chat_ref.username,
        chat_type=chat_ref.chat_type,
    )

    text = ui.format_chat_saved(
        title=chat_ref.title,
        chat_type=chat_ref.chat_type,
        chat_id=chat_ref.chat_id,
        username=chat_ref.username,
        is_new=is_new,
    )

    target = edit or message
    if edit:
        await target.edit_text(text, reply_markup=ui.back_to_menu_keyboard())
    else:
        await target.answer(text, reply_markup=ui.back_to_menu_keyboard())
