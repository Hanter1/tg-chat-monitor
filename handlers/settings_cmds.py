from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import bot_ui as ui
import database as db
from handlers.context import BotContext
from handlers.filters import admin_callback_only, admin_only, safe_edit_callback


def register_settings_handlers(ctx: BotContext) -> Router:
    router = Router(name="settings")
    admin_filter = admin_only(ctx.settings)
    admin_cb_filter = admin_callback_only(ctx.settings)

    async def render_settings_menu(callback: CallbackQuery) -> None:
        bot_settings = await db.get_bot_settings()
        await safe_edit_callback(
            callback,
            ui.format_settings(
                bot_settings.notify_mode,
                bot_settings.poll_interval,
            ),
            reply_markup=ui.settings_keyboard(
                bot_settings.notify_mode,
                bot_settings.poll_interval,
            ),
        )

    @router.callback_query(F.data == "settings:menu", admin_cb_filter)
    async def cb_settings_menu(callback: CallbackQuery) -> None:
        await render_settings_menu(callback)

    @router.callback_query(F.data == "settings:noop", admin_cb_filter)
    async def cb_settings_noop(callback: CallbackQuery) -> None:
        pass

    @router.callback_query(F.data.startswith("settings:notify:"), admin_cb_filter)
    async def cb_settings_notify(callback: CallbackQuery) -> None:
        mode = callback.data.split(":")[2]
        await db.update_bot_settings(notify_mode=mode)
        await ctx.notifier.refresh_settings()
        if mode == "instant":
            await ctx.notifier.flush_digest()
        await render_settings_menu(callback)

    @router.callback_query(F.data.startswith("settings:poll:"), admin_cb_filter)
    async def cb_settings_poll(callback: CallbackQuery) -> None:
        poll = int(callback.data.split(":")[2])
        await db.update_bot_settings(poll_interval=poll)
        await render_settings_menu(callback)

    @router.callback_query(F.data.startswith("matches:"), admin_cb_filter)
    async def cb_matches(callback: CallbackQuery) -> None:
        records = await db.get_recent_matches(15)
        await safe_edit_callback(
            callback,
            ui.format_matches_journal(records),
            reply_markup=ui.matches_keyboard(records) or ui.back_to_menu_keyboard(),
        )

    @router.message(Command("matches"), admin_filter)
    async def cmd_matches(message: Message) -> None:
        records = await db.get_recent_matches(15)
        await message.answer(
            ui.format_matches_journal(records),
            reply_markup=ui.matches_keyboard(records) or ui.back_to_menu_keyboard(),
        )

    @router.message(Command("settings"), admin_filter)
    async def cmd_settings(message: Message) -> None:
        bot_settings = await db.get_bot_settings()
        await message.answer(
            ui.format_settings(
                bot_settings.notify_mode,
                bot_settings.poll_interval,
            ),
            reply_markup=ui.settings_keyboard(
                bot_settings.notify_mode,
                bot_settings.poll_interval,
            ),
        )

    return router
