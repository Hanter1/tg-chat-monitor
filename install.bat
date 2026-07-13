@echo off
chcp 65001 >nul
title tg-chat-monitor — Установка
cd /d "%~dp0"

echo.
echo   ============================================================
echo     tg-chat-monitor — установщик для Windows
echo   ============================================================
echo.
echo   Папка проекта:
echo     %~dp0
echo.
echo   Этот скрипт автоматически:
echo     - скачает и установит Python (если его нет)
echo     - создаст виртуальное окружение
echo     - установит все зависимости
echo     - откроет мастер настройки в браузере
echo     - создаст ярлык на рабочем столе
echo     - предложит запустить бота
echo.
echo   Нужен доступ в интернет. Установка займёт несколько минут.
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\windows\install.ps1"
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% neq 0 (
    echo.
    echo   Установка завершилась с ошибкой.
    pause
    exit /b %EXIT_CODE%
)

exit /b 0
