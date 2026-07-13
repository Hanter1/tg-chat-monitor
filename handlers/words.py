from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import bot_ui as ui
import database as db
from handlers.context import BotContext
from handlers.filters import admin_callback_only, admin_only, answer_callback, safe_edit_callback
from handlers.states import AddWordState


def register_word_handlers(ctx: BotContext) -> Router:
    router = Router(name="words")
    admin_filter = admin_only(ctx.settings)
    admin_cb_filter = admin_callback_only(ctx.settings)

    async def render_words_list(callback: CallbackQuery, page: int) -> None:
        words = await db.get_all_keywords()
        await safe_edit_callback(
            callback,
            ui.format_words_list(words, page),
            reply_markup=ui.words_keyboard(words, page),
        )

    @router.callback_query(F.data == "add:word", admin_cb_filter)
    async def cb_add_word_prompt(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(AddWordState.waiting_word)
        await callback.message.answer(
            "🔑 <b>Новое ключевое слово</b>\n"
            "──────────────────\n\n"
            "Отправьте слово или фразу.\n"
            "<i>/menu — отмена</i>",
        )

    @router.message(AddWordState.waiting_word, admin_filter)
    async def on_word_input(message: Message, state: FSMContext) -> None:
        word = (message.text or "").strip()
        if word.startswith("/"):
            await state.clear()
            await message.answer("Добавление слова отменено.")
            return

        if not word:
            await message.answer("Отправьте непустое слово или /menu для отмены.")
            return

        await state.clear()
        if await db.add_keyword(word):
            await message.answer(
                f"✅ Ключевое слово добавлено: <code>{word.lower()}</code>",
                reply_markup=ui.back_to_menu_keyboard(),
            )
        else:
            await message.answer(
                f"ℹ️ Слово <code>{word.lower()}</code> уже есть в списке.",
                reply_markup=ui.back_to_menu_keyboard(),
            )

    @router.callback_query(F.data.startswith("words:"), admin_cb_filter)
    async def cb_words_list(callback: CallbackQuery) -> None:
        page = int(callback.data.split(":")[1])
        await render_words_list(callback, page)

    @router.callback_query(F.data.startswith("word:view:"), admin_cb_filter)
    async def cb_word_view(callback: CallbackQuery) -> None:
        word = callback.data.split(":", 2)[2]
        await safe_edit_callback(
            callback,
            f"🔑 <b>{escape(word)}</b>\n"
            "──────────────────\n\n"
            "Удалить это ключевое слово?",
            reply_markup=ui.word_delete_confirm_keyboard(word),
        )

    @router.callback_query(F.data.startswith("word:del_yes:"), admin_cb_filter)
    async def cb_word_delete(callback: CallbackQuery) -> None:
        word = callback.data.split(":", 2)[2]
        await db.remove_keyword(word)
        await answer_callback(callback, f"Удалено: {word}")
        await render_words_list(callback, 0)

    @router.message(Command("add_word"), admin_filter)
    async def cmd_add_word(message: Message, command: CommandObject) -> None:
        word = (command.args or "").strip()
        if not word:
            await message.answer("Использование: /add_word [слово]")
            return
        if await db.add_keyword(word):
            await message.answer(
                f"✅ Добавлено: <code>{word.lower()}</code>",
                reply_markup=ui.back_to_menu_keyboard(),
            )
        else:
            await message.answer(f"ℹ️ Слово <code>{word.lower()}</code> уже есть.")

    @router.message(Command("remove_word"), admin_filter)
    async def cmd_remove_word(message: Message, command: CommandObject) -> None:
        word = (command.args or "").strip()
        if not word:
            await message.answer("Использование: /remove_word [слово]")
            return
        if await db.remove_keyword(word):
            await message.answer(
                f"🗑 Удалено: <code>{word.lower()}</code>",
                reply_markup=ui.back_to_menu_keyboard(),
            )
        else:
            await message.answer("Слово не найдено.")

    @router.message(Command("list_words"), admin_filter)
    async def cmd_list_words(message: Message) -> None:
        words = await db.get_all_keywords()
        await message.answer(
            ui.format_words_list(words, 0),
            reply_markup=ui.words_keyboard(words, 0),
        )

    return router
