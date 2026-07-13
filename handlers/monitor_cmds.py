from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
from handlers.context import BotContext
from handlers.filters import admin_callback_only, admin_only, answer_callback
from handlers.menu import render_menu


def register_monitor_handlers(ctx: BotContext) -> Router:
    router = Router(name="monitor")
    admin_filter = admin_only(ctx.settings)
    admin_cb_filter = admin_callback_only(ctx.settings)

    @router.callback_query(F.data == "mon:start", admin_cb_filter)
    async def cb_start_monitor(callback: CallbackQuery) -> None:
        stats = await db.get_stats()
        if stats["active_chats"] == 0:
            await answer_callback(callback, "Нет активных чатов", show_alert=True)
            return
        if stats["words"] == 0:
            await answer_callback(callback, "Сначала добавьте слова", show_alert=True)
            return
        if ctx.monitor.is_running:
            await answer_callback(callback, "Уже запущен")
            await render_menu(callback, ctx, edit=True)
            return

        try:
            await ctx.monitor.start()
        except RuntimeError as exc:
            await answer_callback(callback, str(exc), show_alert=True)
            return

        await answer_callback(callback, "Мониторинг запущен")
        await render_menu(callback, ctx, edit=True)

    @router.callback_query(F.data == "mon:stop", admin_cb_filter)
    async def cb_stop_monitor(callback: CallbackQuery) -> None:
        if not ctx.monitor.is_running:
            await answer_callback(callback, "Мониторинг не запущен")
            return
        await ctx.monitor.stop()
        await answer_callback(callback, "Мониторинг остановлен")
        await render_menu(callback, ctx, edit=True)

    @router.message(Command("start_monitor"), admin_filter)
    async def cmd_start_monitor(message: Message) -> None:
        stats = await db.get_stats()
        if stats["active_chats"] == 0 or stats["words"] == 0:
            await message.answer("Добавьте активные чаты и слова перед запуском. /menu")
            return
        if ctx.monitor.is_running:
            await message.answer("Мониторинг уже запущен.")
            return
        try:
            await ctx.monitor.start()
        except RuntimeError as exc:
            await message.answer(str(exc))
            return
        await render_menu(message, ctx)

    @router.message(Command("stop_monitor"), admin_filter)
    async def cmd_stop_monitor(message: Message) -> None:
        if not ctx.monitor.is_running:
            await message.answer("Мониторинг не запущен.")
            return
        await ctx.monitor.stop()
        await render_menu(message, ctx)

    return router
