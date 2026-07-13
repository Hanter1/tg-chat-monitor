@echo off
chcp 65001 >nul
title tg-chat-monitor
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo.
    echo   Виртуальное окружение не найдено.
    echo   Сначала запустите install.bat
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo.
    echo   Файл .env не найден.
    echo   Запустите install.bat или: venv\Scripts\python.exe setup.py
    echo.
    pause
    exit /b 1
)

echo.
echo   Запуск tg-chat-monitor...
echo   Для остановки нажмите Ctrl+C
echo.

venv\Scripts\python.exe main.py
if errorlevel 1 pause
