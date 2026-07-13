from services.scan_config import SCAN_LIMIT_OPTIONS, SCAN_PERIOD_OPTIONS, ScanConfig


def test_scan_config_normalized_snaps_period():
    config = ScanConfig(period_days=6, limit_per_chat=100, mode="timeline").normalized()
    assert config.period_days in SCAN_PERIOD_OPTIONS
    assert config.period_days == 7


def test_scan_config_normalized_clamps_limit():
    config = ScanConfig(period_days=7, limit_per_chat=15000, mode="timeline").normalized()
    assert config.limit_per_chat == 10000

    config = ScanConfig(period_days=7, limit_per_chat=5, mode="timeline").normalized()
    assert config.limit_per_chat == 20


def test_scan_config_period_all_history():
    config = ScanConfig(period_days=0, limit_per_chat=100, mode="timeline").normalized()
    assert config.period_days == 0
    assert config.period_label() == "Вся история"


def test_scan_config_period_one_year():
    config = ScanConfig(period_days=365, limit_per_chat=100, mode="timeline").normalized()
    assert config.period_days == 365
    assert config.period_label() == "1 год"


def test_scan_config_invalid_mode_defaults_timeline():
    config = ScanConfig(period_days=7, limit_per_chat=100, mode="invalid").normalized()
    assert config.mode == "timeline"


def test_scan_config_summary_line_timeline():
    config = ScanConfig(period_days=7, limit_per_chat=100, mode="timeline")
    text = config.summary_line()
    assert "7 дней" in text
    assert "сообщ. в чате" in text


def test_scan_config_summary_line_search():
    config = ScanConfig(period_days=14, limit_per_chat=200, mode="search")
    text = config.summary_line()
    assert "14 дней" in text
    assert "совпадений на слово" in text


def test_scan_limit_options_values():
    assert 100 in SCAN_LIMIT_OPTIONS
    assert 7 in SCAN_PERIOD_OPTIONS
