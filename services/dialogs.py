from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User
from telethon.utils import get_peer_id

from bot_ui import PAGE_SIZE
from utils import detect_entity_chat_type


async def fetch_dialogs_page(telethon: TelegramClient, page: int) -> tuple[list[dict], int]:
    dialogs: list[dict] = []
    async for dialog in telethon.iter_dialogs():
        entity = dialog.entity
        if not isinstance(entity, (User, Channel, Chat)):
            continue

        dialogs.append(
            {
                "chat_id": get_peer_id(entity),
                "title": dialog.title or dialog.name or str(entity.id),
                "username": getattr(entity, "username", None),
                "chat_type": detect_entity_chat_type(entity),
            }
        )

    dialogs.sort(key=lambda item: item["title"].lower())
    start = page * PAGE_SIZE
    return dialogs[start : start + PAGE_SIZE], len(dialogs)
