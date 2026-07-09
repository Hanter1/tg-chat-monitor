import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import database as db
from config import Settings
from monitor import ChatMonitor

logger = logging.getLogger(__name__)
router = Router()


def _extract_forwarded_chat(message: Message):
    if message.forward_from_chat:
        return message.forward_from_chat

    origin = message.forward_origin
    if origin and getattr(origin, "chat", None):
        return origin.chat

    return None


def _admin_only(settings: Settings):
    def check(message: Message) -> bool:
        return message.from_user is not None and message.from_user.id == settings.admin_user_id

    return check


def setup_router(settings: Settings, monitor: ChatMonitor) -> Router:
    admin_filter = _admin_only(settings)

    @router.message(Command("start"), admin_filter)
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Бот-наблюдатель готов.\n\n"
            "Команды:\n"
            "/add_chat — перешлите сообщение из целевого чата\n"
            "/add_word [слово] — добавить ключевое слово\n"
            "/list_chats — список отслеживаемых чатов\n"
            "/list_words — список ключевых слов\n"
            "/start_monitor — запустить мониторинг\n"
            "/stop_monitor — остановить мониторинг"
        )

    @router.message(Command("add_chat"), admin_filter)
    async def cmd_add_chat(message: Message) -> None:
        source = message
        if message.reply_to_message:
            source = message.reply_to_message

        forwarded_chat = _extract_forwarded_chat(source)
        if not forwarded_chat:
            await message.answer(
                "Перешлите любое сообщение из целевого чата вместе с командой /add_chat "
                "или ответьте /add_chat на пересланное сообщение."
            )
            return

        if forwarded_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
            await message.answer("Можно добавлять только группы, супергруппы и каналы.")
            return

        is_new = await db.add_chat(
            chat_id=forwarded_chat.id,
            title=forwarded_chat.title or str(forwarded_chat.id),
            username=forwarded_chat.username,
        )

        username_info = f" (@{forwarded_chat.username})" if forwarded_chat.username else " (приватный)"
        if is_new:
            await message.answer(
                f"Чат добавлен: {forwarded_chat.title}{username_info}\n"
                f"ID: {forwarded_chat.id}"
            )
        else:
            await message.answer(
                f"Чат уже был в списке, данные обновлены: {forwarded_chat.title}{username_info}"
            )

    @router.message(Command("add_word"), admin_filter)
    async def cmd_add_word(message: Message, command: CommandObject) -> None:
        word = (command.args or "").strip()
        if not word:
            await message.answer("Использование: /add_word [слово]")
            return

        if await db.add_keyword(word):
            await message.answer(f"Ключевое слово добавлено: {word.lower()}")
        else:
            await message.answer(f"Слово «{word.lower()}» уже есть в базе.")

    @router.message(Command("list_chats"), admin_filter)
    async def cmd_list_chats(message: Message) -> None:
        chats = await db.get_all_chats()
        if not chats:
            await message.answer("Список чатов пуст. Используйте /add_chat.")
            return

        lines = []
        for chat in chats:
            uname = f" @{chat.username}" if chat.username else ""
            lines.append(f"• {chat.title}{uname} (id: {chat.chat_id})")
        await message.answer("Отслеживаемые чаты:\n" + "\n".join(lines))

    @router.message(Command("list_words"), admin_filter)
    async def cmd_list_words(message: Message) -> None:
        words = await db.get_all_keywords()
        if not words:
            await message.answer("Ключевые слова не заданы. Используйте /add_word.")
            return
        await message.answer("Ключевые слова:\n" + "\n".join(f"• {w}" for w in words))

    @router.message(Command("start_monitor"), admin_filter)
    async def cmd_start_monitor(message: Message) -> None:
        chats = await db.get_all_chats()
        keywords = await db.get_all_keywords()

        if not chats:
            await message.answer("Сначала добавьте чаты через /add_chat.")
            return
        if not keywords:
            await message.answer("Сначала добавьте ключевые слова через /add_word.")
            return

        if monitor.is_running:
            await message.answer("Мониторинг уже запущен.")
            return

        try:
            await monitor.start()
        except RuntimeError as exc:
            await message.answer(str(exc))
            return

        await message.answer(
            f"Мониторинг запущен.\n"
            f"Чатов: {len(chats)}, ключевых слов: {len(keywords)}.\n"
            f"Интервал опроса: {settings.poll_interval} сек."
        )

    @router.message(Command("stop_monitor"), admin_filter)
    async def cmd_stop_monitor(message: Message) -> None:
        if not monitor.is_running:
            await message.answer("Мониторинг не запущен.")
            return
        await monitor.stop()
        await message.answer("Мониторинг остановлен.")

    @router.message(F.chat.type == ChatType.PRIVATE, admin_filter)
    async def unknown_private(message: Message) -> None:
        if message.text and message.text.startswith("/"):
            await message.answer("Неизвестная команда. Отправьте /start для списка команд.")

    return router


async def create_dispatcher(settings: Settings, monitor: ChatMonitor) -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(setup_router(settings, monitor))
    return dp
