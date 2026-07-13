from datetime import datetime, timedelta, timezone

from services.scan_dates import message_date_utc, message_in_scan_period, utc_cutoff


class FakeMessage:
    def __init__(self, date: datetime) -> None:
        self.date = date


def test_utc_cutoff_is_in_past():
    cutoff = utc_cutoff(7)
    assert cutoff < datetime.now(timezone.utc)


def test_message_date_utc_naive_treated_as_utc():
    naive = datetime(2025, 1, 1, 12, 0, 0)
    result = message_date_utc(FakeMessage(naive))
    assert result.tzinfo == timezone.utc


def test_message_in_scan_period_recent():
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    assert message_in_scan_period(FakeMessage(recent), 7) is True


def test_utc_cutoff_all_history():
    cutoff = utc_cutoff(0)
    assert cutoff.year == 1


def test_message_in_scan_period_old():
    old = datetime.now(timezone.utc) - timedelta(days=30)
    assert message_in_scan_period(FakeMessage(old), 7) is False
