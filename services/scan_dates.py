from datetime import datetime, timedelta, timezone


def utc_cutoff(period_days: int) -> datetime:
    if period_days <= 0:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - timedelta(days=period_days)


def message_date_utc(message) -> datetime:
    dt = message.date
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def message_in_scan_period(message, period_days: int) -> bool:
    if period_days <= 0:
        return True
    return message_date_utc(message) >= utc_cutoff(period_days)
