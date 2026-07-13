from __future__ import annotations

from dataclasses import dataclass

from database import BotSettings

SCAN_PERIOD_OPTIONS = (1, 3, 7, 14, 30, 90, 365, 0)
SCAN_LIMIT_OPTIONS = (50, 100, 200, 500, 1000, 2000)
SCAN_MODES = ("timeline", "search")

SCAN_PERIOD_LABELS = {
    1: "24 часа",
    3: "3 дня",
    7: "7 дней",
    14: "14 дней",
    30: "30 дней",
    90: "90 дней",
    365: "1 год",
    0: "Вся история",
}

SCAN_MODE_LABELS = {
    "timeline": "📅 По периоду",
    "search": "🔎 Поиск Telegram",
}


@dataclass(frozen=True)
class ScanConfig:
    period_days: int = 7
    limit_per_chat: int = 100
    mode: str = "timeline"

    def normalized(self) -> ScanConfig:
        period = self.period_days
        if period not in SCAN_PERIOD_OPTIONS:
            period = min(SCAN_PERIOD_OPTIONS, key=lambda x: abs(x - period))

        limit = max(20, min(self.limit_per_chat, 10000))
        mode = self.mode if self.mode in SCAN_MODES else "timeline"
        return ScanConfig(period_days=period, limit_per_chat=limit, mode=mode)

    @classmethod
    def from_bot_settings(cls, settings: BotSettings) -> ScanConfig:
        period = getattr(settings, "scan_period_days", 7)
        mode = getattr(settings, "scan_mode", "timeline")
        return cls(
            period_days=period,
            limit_per_chat=settings.scan_history_limit,
            mode=mode,
        ).normalized()

    def period_label(self) -> str:
        if self.period_days in SCAN_PERIOD_LABELS:
            return SCAN_PERIOD_LABELS[self.period_days]
        if self.period_days <= 0:
            return SCAN_PERIOD_LABELS[0]
        return f"{self.period_days} дн."

    def mode_label(self) -> str:
        return SCAN_MODE_LABELS.get(self.mode, self.mode)

    def summary_line(self) -> str:
        if self.mode == "search":
            depth = f"до <b>{self.limit_per_chat}</b> совпадений на слово"
        else:
            depth = f"до <b>{self.limit_per_chat}</b> сообщ. в чате"
        return (
            f"📅 Период: <b>{self.period_label()}</b>\n"
            f"⚙️ Режим: <b>{self.mode_label()}</b>\n"
            f"📏 Охват: {depth}"
        )
