#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "  tg-chat-monitor — мастер настройки"
echo ""

if command -v python3 &>/dev/null; then
    exec python3 setup.py "$@"
elif command -v python &>/dev/null; then
    exec python setup.py "$@"
else
    echo "Ошибка: Python не найден. Установите Python 3.10+."
    exit 1
fi
