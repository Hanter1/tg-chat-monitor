import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import bot_ui as ui
import database as db
from handlers.context import BotContext
from handlers.filters import admin_callback_only, admin_only, answer_callback, safe_edit_callback
from services.scan_config import SCAN_LIMIT_OPTIONS, SCAN_PERIOD_OPTIONS, ScanConfig

logger = logging.getLogger(__name__)


def register_history_handlers(ctx: BotContext) -> Router:
    router = Router(name="history")
    admin_filter = admin_only(ctx.settings)
    admin_cb_filter = admin_callback_only(ctx.settings)

    async def load_scan_config() -> ScanConfig:
        return ScanConfig.from_bot_settings(await db.get_bot_settings())

    async def render_scan_menu(callback: CallbackQuery) -> None:
        config = await load_scan_config()
        await safe_edit_callback(
            callback,
            ui.format_scan_menu(config),
            reply_markup=ui.scan_menu_keyboard(config),
        )

    def build_scan_config(
        base: ScanConfig,
        *,
        period_days: int | None = None,
        limit_per_chat: int | None = None,
        mode: str | None = None,
    ) -> ScanConfig:
        return ScanConfig(
            period_days=period_days if period_days is not None else base.period_days,
            limit_per_chat=limit_per_chat if limit_per_chat is not None else base.limit_per_chat,
            mode=mode if mode is not None else base.mode,
        ).normalized()

    def parse_scan_args(args: list[str]) -> tuple[int | None, int | None]:
        nums = [int(arg) for arg in args if arg.lstrip("-").isdigit()]
        if not nums:
            return None, None
        if len(nums) == 1:
            if nums[0] in SCAN_PERIOD_OPTIONS:
                return nums[0], None
            return None, nums[0]
        period, limit = nums[0], nums[1]
        if period not in SCAN_PERIOD_OPTIONS:
            return None, period
        return period, limit

    async def run_history_scan(
        message: Message,
        *,
        chat_id: int | None = None,
        period_days: int | None = None,
        limit_per_chat: int | None = None,
    ) -> None:
        if ctx.history_scanner.is_scanning:
            await message.answer("⏳ Мониторинг уже выполняется.")
            return

        base_config = await load_scan_config()
        config = build_scan_config(
            base_config,
            period_days=period_days,
            limit_per_chat=limit_per_chat,
        )

        progress = await message.answer(
            "🔍 <b>Мониторинг</b>\n"
            "──────────────────\n\n"
            f"{config.summary_line()}\n\n"
            "<i>Запускаю...</i>",
        )
        try:
            await ctx.history_scanner.scan(
                chat_id=chat_id,
                config=config,
                progress_message=progress,
            )
            await progress.edit_reply_markup(reply_markup=ui.scan_done_keyboard())
        except ValueError as exc:
            await progress.edit_text(f"⚠️ {exc}", reply_markup=ui.back_to_menu_keyboard())
        except RuntimeError as exc:
            await progress.edit_text(f"⏳ {exc}")
        except Exception:
            logger.exception("Ошибка мониторинга")
            await progress.edit_text(
                "❌ Ошибка при мониторинге. Попробуйте позже.",
                reply_markup=ui.back_to_menu_keyboard(),
            )

    @router.callback_query(F.data == "scan:menu", admin_cb_filter)
    async def cb_scan_menu(callback: CallbackQuery) -> None:
        await render_scan_menu(callback)

    @router.callback_query(F.data == "scan:noop", admin_cb_filter)
    async def cb_scan_noop(callback: CallbackQuery) -> None:
        pass

    @router.callback_query(F.data.startswith("scan:period:"), admin_cb_filter)
    async def cb_scan_period(callback: CallbackQuery) -> None:
        days = int(callback.data.split(":")[2])
        if days in SCAN_PERIOD_OPTIONS:
            await db.update_bot_settings(scan_period_days=days)
        await render_scan_menu(callback)

    @router.callback_query(F.data.startswith("scan:limit:"), admin_cb_filter)
    async def cb_scan_limit(callback: CallbackQuery) -> None:
        limit = int(callback.data.split(":")[2])
        if limit in SCAN_LIMIT_OPTIONS:
            await db.update_bot_settings(scan_history_limit=limit)
        await render_scan_menu(callback)

    @router.callback_query(F.data.startswith("scan:mode:"), admin_cb_filter)
    async def cb_scan_mode(callback: CallbackQuery) -> None:
        mode = callback.data.split(":")[2]
        if mode in ("timeline", "search"):
            await db.update_bot_settings(scan_mode=mode)
        await render_scan_menu(callback)

    @router.callback_query(F.data == "scan:pick_chat", admin_cb_filter)
    async def cb_scan_pick_chat(callback: CallbackQuery) -> None:
        chats = await db.get_all_chats()
        if not chats:
            await answer_callback(callback, "Сначала добавьте чаты в мониторинг", show_alert=True)
            return
        config = await load_scan_config()
        await safe_edit_callback(
            callback,
            "💬 <b>Выберите чат для сканирования</b>\n\n" + config.summary_line(),
            reply_markup=ui.scan_pick_chat_keyboard(chats),
        )

    @router.callback_query(F.data == "scan:run", admin_cb_filter)
    async def cb_scan_run_all(callback: CallbackQuery) -> None:
        await answer_callback(callback, "Запускаю сканирование...")
        await run_history_scan(callback.message)

    @router.callback_query(F.data.startswith("scan:run:"), admin_cb_filter)
    async def cb_scan_run_chat(callback: CallbackQuery) -> None:
        chat_id = int(callback.data.split(":")[2])
        await answer_callback(callback, "Сканирую чат...")
        await run_history_scan(callback.message, chat_id=chat_id)

    @router.message(Command("scan"), admin_filter)
    async def cmd_scan(message: Message, command: CommandObject) -> None:
        args = (command.args or "").strip().split()
        period, limit = parse_scan_args(args)
        await run_history_scan(message, period_days=period, limit_per_chat=limit)

    @router.message(Command("scan_chat"), admin_filter)
    async def cmd_scan_chat(message: Message, command: CommandObject) -> None:
        args = (command.args or "").strip().split()
        if not args:
            await message.answer(
                "Использование: /scan_chat [ID чата] [период] [лимит]\n"
                "Пример: /scan_chat -1001234567890 7 100\n\n"
                "Период: 1, 3, 7, 14, 30, 90, 365 дней или 0 (вся история).\n"
                "Лимит: 50, 100, 200, 500, 1000 или 2000 сообщений.",
                reply_markup=ui.back_to_menu_keyboard(),
            )
            return

        if not args[0].lstrip("-").isdigit():
            await message.answer("Укажите числовой ID чата.")
            return

        chat_id = int(args[0])
        period, limit = parse_scan_args(args[1:])
        await run_history_scan(
            message,
            chat_id=chat_id,
            period_days=period,
            limit_per_chat=limit,
        )

    return router
