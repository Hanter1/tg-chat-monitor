from __future__ import annotations

from datetime import datetime
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import MatchRecord, MonitoredChat
from services.scan_config import SCAN_MODE_LABELS, SCAN_PERIOD_LABELS, ScanConfig

NOTIFY_MODE_LABELS = {
    "instant": "⚡ Сразу",
    "digest_15": "📦 Каждые 15 мин",
    "digest_60": "📦 Каждый час",
}

CHAT_TYPE_META = {
    "private": ("👤", "Личный чат"),
    "group": ("👥", "Группа"),
    "supergroup": ("👥", "Супергруппа"),
    "channel": ("📢", "Канал"),
    "unknown": ("💬", "Чат"),
}

PAGE_SIZE = 8


def _hr(char: str = "─", width: int = 18) -> str:
    return char * width


def _page_footer(page: int, total_pages: int) -> str:
    return f"<i>Стр. {page + 1} / {total_pages}</i>"


def _readiness_bar(active: int, total: int, *, width: int = 8) -> str:
    if total <= 0:
        return "░" * width
    filled = round(width * active / total)
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def _format_match_time(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d.%m · %H:%M")


def chat_type_icon(chat_type: str) -> str:
    return CHAT_TYPE_META.get(chat_type, CHAT_TYPE_META["unknown"])[0]


def chat_type_label(chat_type: str) -> str:
    return CHAT_TYPE_META.get(chat_type, CHAT_TYPE_META["unknown"])[1]


def truncate(text: str, limit: int = 42) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def format_dashboard(
    *,
    is_running: bool,
    chats_count: int,
    active_chats: int,
    words_count: int,
    poll_interval: int,
    notify_mode: str,
    matches_today: int,
) -> str:
    notify_label = NOTIFY_MODE_LABELS.get(notify_mode, notify_mode)
    ready = active_chats > 0 and words_count > 0
    chats_bar = _readiness_bar(active_chats, chats_count)

    if is_running:
        status_block = (
            "🟢 <b>Мониторинг активен</b>\n"
            f"<i>⚡ realtime · резерв каждые {poll_interval} сек</i>"
        )
    else:
        status_block = "🔴 <b>Мониторинг остановлен</b>"

    lines = [
        "🔭 <b>tg-chat-monitor</b>",
        _hr(),
        "",
        status_block,
        "",
        "📊 <b>Сводка</b>",
        f"├ 💬 Чаты <code>{chats_bar}</code>  <b>{active_chats}</b> / {chats_count}",
        f"├ 🔑 Слова ····· <b>{words_count}</b>",
        f"├ 📨 Сегодня ·· <b>{matches_today}</b>",
        f"└ 🔔 Режим ···· <b>{notify_label}</b>",
    ]

    if not ready:
        missing: list[str] = []
        if active_chats == 0:
            missing.append("чат")
        if words_count == 0:
            missing.append("ключевое слово")
        hint = " и ".join(missing)
        lines.extend(
            [
                "",
                f"⚠️ <i>Добавьте {hint}, чтобы запустить мониторинг.</i>",
            ]
        )
    else:
        lines.extend(["", "✅ <i>Всё готово — можно запускать.</i>"])

    return "\n".join(lines)


def format_chat_detail(chat: MonitoredChat) -> str:
    icon = chat_type_icon(chat.chat_type)
    label = chat_type_label(chat.chat_type)
    title = escape(truncate(chat.title, 48))
    username = f"\n<code>@{chat.username}</code>" if chat.username else ""
    status = "🟢 <b>Активен</b>" if chat.is_active else "⏸ <b>На паузе</b>"
    return (
        f"{icon} <b>{title}</b>{username}\n"
        f"{_hr()}\n\n"
        f"📂 <i>{label}</i>\n"
        f"🆔 <code>{chat.chat_id}</code>\n"
        f"📨 Последний msg: <code>{chat.last_message_id}</code>\n"
        f"📍 Статус: {status}"
    )


def format_chat_saved(*, title: str, chat_type: str, chat_id: int, username: str | None, is_new: bool) -> str:
    icon = chat_type_icon(chat_type)
    label = chat_type_label(chat_type)
    action = "✅ <b>Добавлено</b>" if is_new else "🔄 <b>Обновлено</b>"
    user_line = f"\n<code>@{username}</code>" if username else ""
    return (
        f"{action}\n"
        f"{_hr()}\n\n"
        f"{icon} <b>{escape(truncate(title, 48))}</b>{user_line}\n"
        f"<i>{label}</i> · <code>{chat_id}</code>"
    )


def format_chat_line(chat: MonitoredChat, *, index: int | None = None) -> str:
    icon = chat_type_icon(chat.chat_type)
    label = chat_type_label(chat.chat_type)
    title = escape(truncate(chat.title, 44))
    username = f" <code>@{chat.username}</code>" if chat.username else ""
    status = "🟢" if chat.is_active else "⏸"
    prefix = f"<b>{index}.</b> " if index is not None else ""
    return (
        f"{prefix}{status} {icon} <b>{title}</b>{username}\n"
        f"     <i>{label}</i> · <code>{chat.chat_id}</code>"
    )


def format_chats_list(chats: list[MonitoredChat], page: int) -> str:
    if not chats:
        return (
            "💬 <b>Отслеживаемые чаты</b>\n"
            f"{_hr()}\n\n"
            "📭 <i>Список пуст</i>\n\n"
            "<b>Как добавить:</b>\n"
            "1. <b>📡 Мои группы</b> — выбрать из диалогов\n"
            "2. <b>➕ Добавить</b> — инструкция\n"
            "3. <code>/add_chat @username</code>"
        )

    start = page * PAGE_SIZE
    page_chats = chats[start : start + PAGE_SIZE]
    total_pages = max(1, (len(chats) + PAGE_SIZE - 1) // PAGE_SIZE)
    active = sum(1 for chat in chats if chat.is_active)

    lines = [
        f"💬 <b>Чаты</b>  ·  {len(chats)} всего · {active} активных",
        _page_footer(page, total_pages),
        "",
    ]
    for index, chat in enumerate(page_chats, start=start + 1):
        lines.append(format_chat_line(chat, index=index))
        lines.append("")
    return "\n".join(lines).rstrip()


def format_words_list(words: list[str], page: int) -> str:
    if not words:
        return (
            "🔑 <b>Ключевые слова</b>\n"
            f"{_hr()}\n\n"
            "📭 <i>Список пуст</i>\n\n"
            "Нажмите <b>➕ Слово</b> или отправьте:\n"
            "<code>/add_word bitcoin</code>"
        )

    start = page * PAGE_SIZE
    page_words = words[start : start + PAGE_SIZE]
    total_pages = max(1, (len(words) + PAGE_SIZE - 1) // PAGE_SIZE)

    lines = [
        f"🔑 <b>Ключевые слова</b>  ·  {len(words)}",
        _page_footer(page, total_pages),
        "",
    ]
    for index, word in enumerate(page_words, start=start + 1):
        lines.append(f"<b>{index:02d}.</b>  <code>{escape(word)}</code>")
    return "\n".join(lines)


def format_help() -> str:
    return (
        "ℹ️ <b>Справка</b>\n"
        f"{_hr()}\n\n"
        "━━ <b>Чаты и группы</b>\n"
        "• <b>📡 Мои группы</b> — выбор из ваших диалогов\n"
        "• Пересылка + <code>/add_chat</code>\n"
        "• <code>/add_chat @channel</code> или по ID\n\n"
        "━━ <b>Ключевые слова</b>\n"
        "• <b>➕ Слово</b> или <code>/add_word текст</code>\n"
        "• Без учёта регистра, поиск по подстроке\n\n"
        "━━ <b>Мониторинг</b>\n"
        "• <b>▶️ Запустить</b> — realtime + резервный опрос\n"
        "• <b>⏸ Пауза</b> — для отдельного чата в списке\n"
        "• <b>🔍 Мониторинг</b> — сканирование пропущенного\n"
        "• <b>📋 Журнал</b> — последние находки\n\n"
        "━━ <b>Уведомления</b>\n"
        "⚡ сразу · 📦 дайджест 15 мин / 1 час\n\n"
        "━━ <b>Команды</b>\n"
        "/menu · /status · /settings · /matches\n"
        "/remove_chat ID · /remove_word слово"
    )


def format_add_chat_help() -> str:
    return (
        "➕ <b>Добавление чата</b>\n"
        f"{_hr()}\n\n"
        "Выберите удобный способ:\n\n"
        "1️⃣ <b>📡 Мои группы</b>\n"
        "    <i>список ваших диалогов</i>\n\n"
        "2️⃣ <b>Пересылка</b>\n"
        "    ответьте <code>/add_chat</code> на сообщение\n\n"
        "3️⃣ <b>Username</b>\n"
        "    <code>/add_chat @channel</code>\n\n"
        "4️⃣ <b>ID чата</b>\n"
        "    <code>/add_chat -1001234567890</code>"
    )


def format_discover_header(page: int, total_pages: int, total: int) -> str:
    return (
        "📡 <b>Ваши группы и каналы</b>\n"
        f"{_page_footer(page, total_pages)} · всего <b>{total}</b>\n\n"
        "Нажмите на строку, чтобы добавить в мониторинг.\n"
        "<i>✅ — уже отслеживается · ➕ — можно добавить</i>"
    )


def format_scan_menu(config: ScanConfig) -> str:
    if config.period_days <= 0:
        period_hint = "Без ограничения по дате — проверяются сообщения до выбранного лимита."
    elif config.mode == "timeline":
        period_hint = "Просматривает сообщения за выбранный период и ищет ключевые слова."
    else:
        period_hint = "Использует поиск Telegram по каждому ключевому слову."
    return (
        "🔍 <b>Мониторинг</b>\n"
        f"{_hr()}\n\n"
        "Найдёт пропущенные совпадения в сообщениях чатов.\n\n"
        "⚙️ <b>Текущие настройки</b>\n"
        f"{config.summary_line()}\n\n"
        f"<i>{period_hint}</i>"
    )


def scan_menu_keyboard(config: ScanConfig) -> InlineKeyboardMarkup:
    def period_mark(days: int) -> str:
        return "● " if config.period_days == days else ""

    def limit_mark(value: int) -> str:
        return "● " if config.limit_per_chat == value else ""

    def mode_mark(mode: str) -> str:
        return "● " if config.mode == mode else ""

    from services.scan_config import SCAN_LIMIT_OPTIONS, SCAN_PERIOD_OPTIONS

    period_rows = [
        [
            InlineKeyboardButton(
                text=f"{period_mark(days)}{SCAN_PERIOD_LABELS[days]}",
                callback_data=f"scan:period:{days}",
            )
            for days in SCAN_PERIOD_OPTIONS[0:3]
        ],
        [
            InlineKeyboardButton(
                text=f"{period_mark(days)}{SCAN_PERIOD_LABELS[days]}",
                callback_data=f"scan:period:{days}",
            )
            for days in SCAN_PERIOD_OPTIONS[3:6]
        ],
        [
            InlineKeyboardButton(
                text=f"{period_mark(days)}{SCAN_PERIOD_LABELS[days]}",
                callback_data=f"scan:period:{days}",
            )
            for days in SCAN_PERIOD_OPTIONS[6:8]
        ],
    ]
    limit_row_1 = [
        InlineKeyboardButton(
            text=f"{limit_mark(value)}{value}",
            callback_data=f"scan:limit:{value}",
        )
        for value in SCAN_LIMIT_OPTIONS[:3]
    ]
    limit_row_2 = [
        InlineKeyboardButton(
            text=f"{limit_mark(value)}{value}",
            callback_data=f"scan:limit:{value}",
        )
        for value in SCAN_LIMIT_OPTIONS[3:]
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Период", callback_data="scan:noop")],
            *period_rows,
            [InlineKeyboardButton(text="📏 Лимит сообщений", callback_data="scan:noop")],
            limit_row_1,
            limit_row_2,
            [InlineKeyboardButton(text="⚙️ Режим", callback_data="scan:noop")],
            [
                InlineKeyboardButton(
                    text=f"{mode_mark('timeline')}{SCAN_MODE_LABELS['timeline']}",
                    callback_data="scan:mode:timeline",
                ),
                InlineKeyboardButton(
                    text=f"{mode_mark('search')}{SCAN_MODE_LABELS['search']}",
                    callback_data="scan:mode:search",
                ),
            ],
            [InlineKeyboardButton(text="▶️ Сканировать все чаты", callback_data="scan:run")],
            [InlineKeyboardButton(text="💬 Выбрать чат", callback_data="scan:pick_chat")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")],
        ]
    )


def scan_pick_chat_keyboard(chats: list[MonitoredChat]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for chat in chats[:12]:
        icon = chat_type_icon(chat.chat_type)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{icon} {truncate(chat.title, 26)}",
                    callback_data=f"scan:run:{chat.chat_id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text="« Назад", callback_data="scan:menu"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def open_message_callback(chat_id: int, message_id: int) -> str:
    return f"open:{chat_id}:{message_id}"


def format_match_notification(
    *,
    title: str,
    chat_type: str,
    chat_id: int,
    username: str | None,
    message_id: int,
    text: str,
    matched_keywords: list[str],
    historical: bool = False,
    message_link: str | None = None,
) -> tuple[str, LinkPreviewOptions, InlineKeyboardMarkup | None]:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

    icon = chat_type_icon(chat_type)
    label = chat_type_label(chat_type)
    safe_title = escape(truncate(title, 64))
    preview = escape(truncate(text, 500))
    keywords_text = " · ".join(f"<code>{escape(word)}</code>" for word in matched_keywords)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📎 Открыть сообщение",
                    callback_data=open_message_callback(chat_id, message_id),
                )
            ],
            [InlineKeyboardButton(text="📋 Журнал", callback_data="matches:0")],
        ]
    )
    preview_options = LinkPreviewOptions(is_disabled=True)
    link_line = (
        "👇 Нажмите «Открыть» — бот перешлёт сообщение сюда\n"
        "с подписью, из какого чата оно пришло."
    )

    header = "📜 <b>Найдено в истории</b>" if historical else "🔔 <b>Новое совпадение</b>"
    notification = (
        f"{header}\n"
        f"{_hr()}\n\n"
        f"{icon} <b>{safe_title}</b>\n"
        f"<i>{label}</i>\n\n"
        f"🔑 {keywords_text}\n\n"
        f"💬 <i>{preview}</i>\n\n"
        f"{link_line}"
    )
    return notification, preview_options, keyboard


def main_menu_keyboard(*, is_running: bool, can_start: bool) -> InlineKeyboardMarkup:
    if is_running:
        row_monitor = [
            InlineKeyboardButton(text="🟢 Работает", callback_data="menu:main"),
            InlineKeyboardButton(text="⏹ Стоп", callback_data="mon:stop"),
        ]
    elif can_start:
        row_monitor = [InlineKeyboardButton(text="▶️ Запустить", callback_data="mon:start")]
    else:
        row_monitor = [InlineKeyboardButton(text="⚠️ Не готов", callback_data="menu:main")]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            row_monitor,
            [
                InlineKeyboardButton(text="💬 Чаты", callback_data="chats:0"),
                InlineKeyboardButton(text="🔑 Слова", callback_data="words:0"),
            ],
            [
                InlineKeyboardButton(text="📡 Группы", callback_data="discover:0"),
                InlineKeyboardButton(text="➕ Чат", callback_data="add:chat"),
            ],
            [
                InlineKeyboardButton(text="➕ Слово", callback_data="add:word"),
                InlineKeyboardButton(text="🔍 Мониторинг", callback_data="scan:menu"),
            ],
            [
                InlineKeyboardButton(text="📋 Журнал", callback_data="matches:0"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu"),
            ],
            [InlineKeyboardButton(text="ℹ️ Справка", callback_data="help")],
        ]
    )


def chats_keyboard(chats: list[MonitoredChat], page: int) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    page_chats = chats[start : start + PAGE_SIZE]
    total_pages = max(1, (len(chats) + PAGE_SIZE - 1) // PAGE_SIZE)

    rows: list[list[InlineKeyboardButton]] = []
    for chat in page_chats:
        icon = chat_type_icon(chat.chat_type)
        status = "⏸" if not chat.is_active else "🟢"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {icon} {truncate(chat.title, 24)}",
                    callback_data=f"chat:view:{chat.chat_id}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"chats:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"· {page + 1}/{total_pages} ·", callback_data="menu:main"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"chats:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(text="➕ Чат", callback_data="add:chat"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chat_actions_keyboard(chat_id: int, *, is_active: bool) -> InlineKeyboardMarkup:
    toggle_label = "⏸ Пауза" if is_active else "▶️ Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=toggle_label, callback_data=f"chat:toggle:{chat_id}"),
                InlineKeyboardButton(text="🔍 Мониторинг", callback_data=f"scan:run:{chat_id}"),
            ],
            [
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"chat:del:{chat_id}"),
            ],
            [
                InlineKeyboardButton(text="« К списку", callback_data="chats:0"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
            ],
        ]
    )


def chat_delete_confirm_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"chat:del_yes:{chat_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"chat:view:{chat_id}"),
            ]
        ]
    )


def words_keyboard(words: list[str], page: int) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    page_words = words[start : start + PAGE_SIZE]
    total_pages = max(1, (len(words) + PAGE_SIZE - 1) // PAGE_SIZE)

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for word in page_words:
        row.append(
            InlineKeyboardButton(text=f"· {truncate(word, 14)}", callback_data=f"word:view:{word}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"words:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="menu:main"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"words:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append(
        [
            InlineKeyboardButton(text="➕ Слово", callback_data="add:word"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def word_delete_confirm_keyboard(word: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Удалить", callback_data=f"word:del_yes:{word}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="words:0"),
            ]
        ]
    )


def discover_keyboard(
    items: list[dict],
    page: int,
    total: int,
    monitored_ids: set[int],
) -> InlineKeyboardMarkup:
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    rows: list[list[InlineKeyboardButton]] = []

    for item in items:
        icon = chat_type_icon(item["chat_type"])
        prefix = "✅" if item["chat_id"] in monitored_ids else "➕"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix} {icon} {truncate(item['title'], 28)}",
                    callback_data=f"discover:add:{item['chat_id']}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"discover:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="menu:main"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"discover:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def scan_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Журнал", callback_data="matches:0"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main"),
            ]
        ]
    )


def format_settings(notify_mode: str, poll_interval: int) -> str:
    notify_label = NOTIFY_MODE_LABELS.get(notify_mode, notify_mode)
    return (
        "⚙️ <b>Настройки</b>\n"
        f"{_hr()}\n\n"
        "🔔 <b>Уведомления</b>\n"
        f"    {notify_label}\n\n"
        "⏱ <b>Резервный опрос</b>\n"
        f"    каждые <b>{poll_interval}</b> сек\n\n"
        "<i>Настройки мониторинга — в меню «🔍 Мониторинг».</i>"
    )


def settings_keyboard(notify_mode: str, poll_interval: int) -> InlineKeyboardMarkup:
    def mark(mode: str) -> str:
        return "● " if notify_mode == mode else "○ "

    def poll_mark(value: int) -> str:
        return "● " if poll_interval == value else "○ "

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings:noop")],
            [
                InlineKeyboardButton(text=f"{mark('instant')}⚡ Сразу", callback_data="settings:notify:instant"),
            ],
            [
                InlineKeyboardButton(
                    text=f"{mark('digest_15')}📦 15 мин",
                    callback_data="settings:notify:digest_15",
                ),
                InlineKeyboardButton(
                    text=f"{mark('digest_60')}📦 1 час",
                    callback_data="settings:notify:digest_60",
                ),
            ],
            [InlineKeyboardButton(text="⏱ Резервный опрос", callback_data="settings:noop")],
            [
                InlineKeyboardButton(text=f"{poll_mark(10)}10с", callback_data="settings:poll:10"),
                InlineKeyboardButton(text=f"{poll_mark(30)}30с", callback_data="settings:poll:30"),
                InlineKeyboardButton(text=f"{poll_mark(60)}60с", callback_data="settings:poll:60"),
            ],
            [InlineKeyboardButton(text="🔍 Мониторинг", callback_data="scan:menu")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")],
        ]
    )


def format_matches_journal(records: list[MatchRecord]) -> str:
    if not records:
        return (
            "📋 <b>Журнал совпадений</b>\n"
            f"{_hr()}\n\n"
            "📭 <i>Пока пусто</i>\n\n"
            "Здесь появятся последние находки\n"
            "после запуска мониторинга."
        )

    lines = [
        f"📋 <b>Журнал</b>  ·  последние {len(records)}",
        _hr(),
        "",
    ]
    for index, record in enumerate(records, start=1):
        words = escape(record.keywords.replace(",", " · "))
        preview = escape(truncate(record.text_preview, 64))
        when = _format_match_time(record.created_at)
        time_part = f"  <i>{when}</i>" if when else ""
        lines.append(
            f"<b>{index}.</b> <b>{escape(truncate(record.chat_title, 28))}</b>{time_part}\n"
            f"    🔑 <code>{words}</code>\n"
            f"    💬 {preview}"
        )
        lines.append("")
    return "\n".join(lines).rstrip()


def matches_keyboard(records: list[MatchRecord]) -> InlineKeyboardMarkup | None:
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for index, record in enumerate(records[:10], start=1):
        row.append(
            InlineKeyboardButton(
                text=f"📎 {index}",
                callback_data=open_message_callback(record.chat_id, record.message_id),
            )
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not buttons:
        return None
    buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главная", callback_data="menu:main")]]
    )
