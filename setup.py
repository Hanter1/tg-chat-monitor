#!/usr/bin/env python3
"""
Мастер настройки tg-chat-monitor.

Запустите после клонирования репозитория:
    python setup.py

Откроется браузер с пошаговой настройкой — как веб-интерфейс.
"""

from __future__ import annotations

import argparse
import sys

if sys.version_info < (3, 10):
    print("Ошибка: требуется Python 3.10 или новее.")
    print(f"Текущая версия: {sys.version}")
    sys.exit(1)

from setup.server import DEFAULT_PORT, run_server


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Интерактивный мастер настройки tg-chat-monitor",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Порт веб-интерфейса (по умолчанию {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Не открывать браузер автоматически",
    )
    args = parser.parse_args()

    run_server(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
