# Релизы и подпись APK

Релизы собираются GitHub Actions по тегу `v*` (workflow `.github/workflows/release.yml`).

Артефакты:

- `tg-chat-monitor-<tag>-android.apk` — подписанный release (если настроен keystore)
- `tg-chat-monitor-<tag>-android-debug.apk` — debug (если secrets нет или включён debug)
- `tg-chat-monitor-<tag>-windows.zip` — исходники + `install.bat` / `start.bat`

## Один раз: создать keystore

```bash
keytool -genkey -v \
  -keystore release.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias tgchatmonitor
```

Сохраните `release.jks` и пароли **вне git**.

## GitHub Secrets

В репозитории: **Settings → Secrets and variables → Actions**:

| Secret | Значение |
|--------|----------|
| `KEYSTORE_BASE64` | `base64 -w0 release.jks` (Linux/macOS) или `[Convert]::ToBase64String([IO.File]::ReadAllBytes("release.jks"))` (PowerShell) |
| `KEYSTORE_PASSWORD` | пароль хранилища |
| `KEY_ALIAS` | например `tgchatmonitor` |
| `KEY_PASSWORD` | пароль ключа |

Без этих secrets workflow всё равно соберёт **debug APK** и Windows ZIP.

## Android pip / Chaquopy

Сборка APK ставит зависимости из `android/requirements-android.txt` через Chaquopy.

Два пакета нельзя взять «как есть» с PyPI для Android:

| Пакет | Почему | Откуда берём |
|-------|--------|--------------|
| `pyaes` | на PyPI только sdist | `android/wheels/pyaes-*.whl` (в git) |
| `pydantic-core` | Rust, нужны Android-wheels | CI собирает `v2.41.5` через `cibuildwheel` (Python 3.13) перед Gradle |

Chaquopy в APK использует **Python 3.13** (`android/app/build.gradle.kts`).

## Как выпустить

```bash
git tag v1.0.0
git push origin v1.0.0
```

Дождитесь зелёного workflow **Release** — на странице Releases появятся файлы для скачивания.

## Локальная release-сборка

В `android/local.properties` (файл в `.gitignore`):

```properties
KEYSTORE_PATH=C:/path/to/release.jks
KEYSTORE_PASSWORD=...
KEY_ALIAS=tgchatmonitor
KEY_PASSWORD=...
```

```bash
cd android
./gradlew :app:assembleRelease
```
