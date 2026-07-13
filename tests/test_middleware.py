from pathlib import Path


def test_callback_guard_does_not_monkeypatch_answer():
    source = Path("handlers/middleware.py").read_text(encoding="utf-8")
    assert "event.answer =" not in source
