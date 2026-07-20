# Android — TG Chat Monitor

Приложение запускает тот же Python-монитор (aiogram + Telethon) на телефоне
через [Chaquopy](https://chaquo.com/chaquopy/) и держит процесс живым
с помощью **Foreground Service** (постоянное уведомление).

## Скачать

1. Откройте [Releases](https://github.com/Hanter1/tg-chat-monitor/releases).
2. Скачайте файл `tg-chat-monitor-*-android.apk` (или `*-android-debug.apk`).
3. На телефоне: **Настройки → безопасность → установка неизвестных приложений**
   (для браузера/файлового менеджера, из которого ставите APK).
4. Откройте APK и установите.

## Первый запуск

1. Откройте **TG Chat Monitor**.
2. Вкладка **Настройки** — заполните:
   - `BOT_TOKEN` — от [@BotFather](https://t.me/BotFather)
   - `API_ID` / `API_HASH` — с [my.telegram.org/apps](https://my.telegram.org/apps)
   - `ADMIN_USER_ID` — ваш Telegram ID ([@userinfobot](https://t.me/userinfobot))
3. Сохраните → вкладка **Статус** → **Старт**.
4. При первом запуске введите номер Telethon, код из Telegram и (если нужно) пароль 2FA.
5. Дальше управляйте ботом в Telegram, как на ПК: чаты, слова, `/start_monitor`.

## Батарея и автозапуск (важно)

Android может убить фоновый процесс. Обязательно:

1. В приложении нажмите **Исключить из оптимизации батареи**.
2. На Xiaomi / HyperOS, Huawei, Oppo, Samsung: разрешите **автозапуск** и снимите
   ограничения расхода батареи для TG Chat Monitor в системных настройках.

Без этого мониторинг будет останавливаться при выключенном экране.

## Ограничения

- Телефон должен быть **онлайн**; при выключении или без сети мониторинга нет.
- APK большой (внутри Python runtime).
- Это **не** сервер 24/7 — для постоянной работы надёжнее ПК / VPS / Docker.
- Telethon использует **ваш** аккаунт: вы должны состоять в отслеживаемых чатах.

## Сборка локально

Нужны JDK 17, Android SDK, Python **3.13** (как `buildPython` для Chaquopy):

```bash
cd android
./gradlew :app:assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

Для локальной сборки нужны Android-wheels в `android/wheels/`
(`pyaes` уже в репозитории; `pydantic-core` собирается в CI —
см. [releasing.md](releasing.md)).

Release-подпись — см. [releasing.md](releasing.md).
