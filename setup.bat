@echo off
chcp 65001 >nul
echo.
echo  tg-chat-monitor - мастер настройки
echo.
python setup.py %*
if errorlevel 1 (
    echo.
    echo  Ошибка запуска. Убедитесь, что Python 3.10+ установлен и доступен в PATH.
    pause
)
