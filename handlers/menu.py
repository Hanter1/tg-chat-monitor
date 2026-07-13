from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import bot_ui as ui
import database as db
from handlers.context import BotContext
from handlers.filters import admin_callback_only, admin_only, answer_callback, safe_edit_callback


async def render_menu(
    target: Message | CallbackQuery,
    ctx: BotContext,
    *,
    edit: bool = False,
) -> None:
    stats = await db.get_stats()
    bot_settings = await db.get_bot_settings()
    is_running = ctx.monitor.is_running
    can_start = stats["active_chats"] > 0 and stats["words"] > 0

    text = ui.format_dashboard(
        is_running=is_running,
        chats_count=stats["chats"],
        active_chats=stats["active_chats"],
        words_count=stats["words"],
        poll_interval=bot_settings.poll_interval,
        notify_mode=bot_settings.notify_mode,
        matches_today=stats["matches_today"],
    )
    keyboard = ui.main_menu_keyboard(is_running=is_running, can_start=can_start)

    if isinstance(target, CallbackQuery):
        if edit:
            await safe_edit_callback(target, text, reply_markup=keyboard)
        else:
            await target.message.answer(text, reply_markup=keyboard)
        await answer_callback(target)
    elif edit:
        await target.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)


def register_menu_handlers(ctx: BotContext) -> Router:
    router = Router(name="menu")
    admin_filter = admin_only(ctx.settings)
    admin_cb_filter = admin_callback_only(ctx.settings)

    @router.message(Command("start", "menu"), admin_filter)
    async def cmd_menu(message: Message) -> None:
        await render_menu(message, ctx)

    @router.message(Command("status"), admin_filter)
    async def cmd_status(message: Message) -> None:
        await render_menu(message, ctx)

    @router.message(Command("help"), admin_filter)
    async def cmd_help(message: Message) -> None:
        await message.answer(ui.format_help(), reply_markup=ui.back_to_menu_keyboard())

    @router.callback_query(F.data == "menu:main", admin_cb_filter)
    async def cb_menu(callback: CallbackQuery) -> None:
        await render_menu(callback, ctx, edit=True)

    @router.callback_query(F.data == "help", admin_cb_filter)
    async def cb_help(callback: CallbackQuery) -> None:
        await safe_edit_callback(
            callback,
            ui.format_help(),
            reply_markup=ui.back_to_menu_keyboard(),
        )

    return router
