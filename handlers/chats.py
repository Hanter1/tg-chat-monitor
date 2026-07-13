import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import bot_ui as ui
import database as db
from bot_ui import PAGE_SIZE
from handlers.context import BotContext
from handlers.filters import (
    admin_callback_only,
    admin_only,
    answer_callback,
    safe_edit_callback,
)
from services.chat_resolver import (
    entity_to_chat_ref,
    extract_forwarded_chat,
    forward_failure_hint,
    resolve_chat_reference,
    save_chat,
)
from services.dialogs import fetch_dialogs_page

logger = logging.getLogger(__name__)


def register_chat_handlers(ctx: BotContext) -> Router:
    router = Router(name="chats")
    admin_filter = admin_only(ctx.settings)
    admin_cb_filter = admin_callback_only(ctx.settings)

    async def render_discover(callback: CallbackQuery, page: int) -> None:
        items, total = await fetch_dialogs_page(ctx.telethon, page)
        monitored = {chat.chat_id for chat in await db.get_all_chats()}
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        text = ui.format_discover_header(page, total_pages, total)
        keyboard = ui.discover_keyboard(items, page, total, monitored)
        await safe_edit_callback(callback, text, reply_markup=keyboard)

    async def render_chat_view(callback: CallbackQuery, chat_id: int) -> None:
        chat = await db.get_chat(chat_id)
        if not chat:
            await answer_callback(callback, "Чат не найден", show_alert=True)
            return

        await safe_edit_callback(
            callback,
            ui.format_chat_detail(chat),
            reply_markup=ui.chat_actions_keyboard(chat_id, is_active=chat.is_active),
        )

    @router.callback_query(F.data == "add:chat", admin_cb_filter)
    async def cb_add_chat_help(callback: CallbackQuery) -> None:
        await safe_edit_callback(
            callback,
            ui.format_add_chat_help(),
            reply_markup=ui.back_to_menu_keyboard(),
        )

    @router.callback_query(F.data.startswith("chats:"), admin_cb_filter)
    async def cb_chats_list(callback: CallbackQuery) -> None:
        page = int(callback.data.split(":")[1])
        chats = await db.get_all_chats()
        await safe_edit_callback(
            callback,
            ui.format_chats_list(chats, page),
            reply_markup=ui.chats_keyboard(chats, page),
        )

    @router.callback_query(F.data.startswith("chat:view:"), admin_cb_filter)
    async def cb_chat_view(callback: CallbackQuery) -> None:
        chat_id = int(callback.data.split(":")[2])
        await render_chat_view(callback, chat_id)

    @router.callback_query(
        F.data.startswith("chat:del:") & ~F.data.startswith("chat:del_yes:"),
        admin_cb_filter,
    )
    async def cb_chat_delete(callback: CallbackQuery) -> None:
        chat_id = int(callback.data.split(":")[2])
        chat = await db.get_chat(chat_id)
        if not chat:
            await answer_callback(callback, "Чат не найден", show_alert=True)
            return

        await safe_edit_callback(
            callback,
            f"🗑 <b>Удалить из мониторинга?</b>\n\n{ui.format_chat_line(chat)}",
            reply_markup=ui.chat_delete_confirm_keyboard(chat_id),
        )

    @router.callback_query(F.data.startswith("chat:del_yes:"), admin_cb_filter)
    async def cb_chat_delete_confirm(callback: CallbackQuery) -> None:
        chat_id = int(callback.data.split(":")[2])
        removed = await db.remove_chat(chat_id)
        chats = await db.get_all_chats()
        await safe_edit_callback(
            callback,
            ui.format_chats_list(chats, 0),
            reply_markup=ui.chats_keyboard(chats, 0),
        )
        await answer_callback(callback, "Чат удалён" if removed else "Чат не найден", show_alert=not removed)

    @router.callback_query(F.data.startswith("chat:toggle:"), admin_cb_filter)
    async def cb_chat_toggle(callback: CallbackQuery) -> None:
        chat_id = int(callback.data.split(":")[2])
        new_state = await db.toggle_chat_active(chat_id)
        if new_state is None:
            await answer_callback(callback, "Чат не найден", show_alert=True)
            return
        await answer_callback(callback, "Включён" if new_state else "На паузе")
        await render_chat_view(callback, chat_id)

    @router.callback_query(
        F.data.startswith("discover:") & ~F.data.startswith("discover:add:"),
        admin_cb_filter,
    )
    async def cb_discover(callback: CallbackQuery) -> None:
        page = int(callback.data.split(":")[1])
        await render_discover(callback, page)

    @router.callback_query(F.data.startswith("discover:add:"), admin_cb_filter)
    async def cb_discover_add(callback: CallbackQuery) -> None:
        chat_id = int(callback.data.split(":")[2])
        existing = await db.get_chat(chat_id)
        if existing:
            await answer_callback(callback, "Уже в списке", show_alert=True)
            return

        try:
            entity = await ctx.telethon.get_entity(chat_id)
            chat_ref = entity_to_chat_ref(entity)
        except Exception:
            logger.exception("discover:add failed for %s", chat_id)
            await answer_callback(callback, "Не удалось добавить чат", show_alert=True)
            return

        await db.add_chat(
            chat_ref.chat_id,
            chat_ref.title,
            chat_ref.username,
            chat_ref.chat_type,
        )
        await answer_callback(callback, f"Добавлено: {chat_ref.title[:30]}")
        await render_discover(callback, 0)

    @router.message(Command("add_chat"), admin_filter)
    async def cmd_add_chat(message: Message, command: CommandObject) -> None:
        args = (command.args or "").strip()
        if args:
            chat_ref = await resolve_chat_reference(args, ctx.telethon)
            if not chat_ref:
                await message.answer(
                    f"❌ Не найден чат «{args}».\n"
                    "Попробуйте «📡 Мои группы» в меню /menu"
                )
                return
            await save_chat(message, chat_ref)
            return

        source = message.reply_to_message if message.reply_to_message else message
        chat_ref = extract_forwarded_chat(source)
        if not chat_ref:
            await message.answer(forward_failure_hint(source))
            return
        await save_chat(message, chat_ref)

    @router.message(Command("remove_chat"), admin_filter)
    async def cmd_remove_chat(message: Message, command: CommandObject) -> None:
        arg = (command.args or "").strip()
        if not arg.lstrip("-").isdigit():
            await message.answer("Использование: /remove_chat [ID]")
            return
        if await db.remove_chat(int(arg)):
            await message.answer(
                f"🗑 Чат <code>{arg}</code> удалён.",
                reply_markup=ui.back_to_menu_keyboard(),
            )
        else:
            await message.answer("Чат не найден.")

    @router.message(Command("list_chats"), admin_filter)
    async def cmd_list_chats(message: Message) -> None:
        chats = await db.get_all_chats()
        await message.answer(
            ui.format_chats_list(chats, 0),
            reply_markup=ui.chats_keyboard(chats, 0),
        )

    return router
