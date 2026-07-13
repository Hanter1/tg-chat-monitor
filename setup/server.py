"""Локальный веб-сервер мастера настройки."""

from __future__ import annotations

import json
import mimetypes
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
STATIC_DIR = Path(__file__).resolve().parent / "static"
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements.txt"

DEFAULT_PORT = 8765

FIELD_DEFAULTS: dict[str, str] = {
    "TELETHON_SESSION": "monitor_session",
    "DATABASE_URL": "sqlite+aiosqlite:///./monitor.db",
    "POLL_INTERVAL": "10",
}

REQUIRED_FIELDS = ("BOT_TOKEN", "API_ID", "API_HASH", "ADMIN_USER_ID")


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def build_env_content(values: dict[str, str]) -> str:
    template = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    result_lines: list[str] = []

    for line in template.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            result_lines.append(line)
            continue

        key, _, _ = stripped.partition("=")
        key = key.strip()
        if key in values and values[key]:
            result_lines.append(f"{key}={values[key]}")
        else:
            result_lines.append(line)

    known_keys = {line.split("=", 1)[0].strip() for line in result_lines if "=" in line and not line.strip().startswith("#")}
    for key, value in values.items():
        if key not in known_keys and value:
            result_lines.append(f"{key}={value}")

    return "\n".join(result_lines).rstrip() + "\n"


def validate_settings(values: dict[str, str]) -> list[str]:
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        if not values.get(field, "").strip():
            errors.append(f"Поле {field} обязательно для заполнения")

    bot_token = values.get("BOT_TOKEN", "").strip()
    if bot_token and not re.match(r"^\d+:[A-Za-z0-9_-]+$", bot_token):
        errors.append("BOT_TOKEN должен быть в формате 123456789:ABCdef...")

    api_id = values.get("API_ID", "").strip()
    if api_id and not api_id.isdigit():
        errors.append("API_ID должен быть числом")

    admin_id = values.get("ADMIN_USER_ID", "").strip()
    if admin_id and not admin_id.lstrip("-").isdigit():
        errors.append("ADMIN_USER_ID должен быть числом")

    poll = values.get("POLL_INTERVAL", "10").strip()
    if poll:
        try:
            poll_int = int(poll)
            if poll_int < 5:
                errors.append("POLL_INTERVAL не может быть меньше 5 секунд")
        except ValueError:
            errors.append("POLL_INTERVAL должен быть целым числом")

    return errors


def get_status() -> dict[str, Any]:
    env_exists = ENV_PATH.exists()
    env_values = parse_env_file(ENV_PATH) if env_exists else parse_env_file(ENV_EXAMPLE_PATH)

    for key, default in FIELD_DEFAULTS.items():
        env_values.setdefault(key, default)

    venv_candidates = [PROJECT_ROOT / "venv", PROJECT_ROOT / ".venv"]
    venv_exists = any(path.exists() for path in venv_candidates)

    deps_installed = False
    try:
        import aiogram  # noqa: F401

        deps_installed = True
    except ImportError:
        pass

    return {
        "project_root": str(PROJECT_ROOT),
        "env_exists": env_exists,
        "env_path": str(ENV_PATH),
        "values": env_values,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "python_ok": sys.version_info >= (3, 10),
        "venv_exists": venv_exists,
        "deps_installed": deps_installed,
        "requirements_exists": REQUIREMENTS_PATH.exists(),
    }


def install_dependencies() -> dict[str, Any]:
    if not REQUIREMENTS_PATH.exists():
        return {"ok": False, "message": "Файл requirements.txt не найден"}

    python_exe = _resolve_python_executable()

    try:
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return {"ok": False, "message": str(exc)}

    if result.returncode != 0:
        return {
            "ok": False,
            "message": "Не удалось установить зависимости",
            "details": (result.stderr or result.stdout).strip(),
        }

    return {"ok": True, "message": "Зависимости успешно установлены"}


def _resolve_python_executable() -> Path:
    venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def launch_application() -> dict[str, Any]:
    if not ENV_PATH.exists():
        return {"ok": False, "message": "Сначала сохраните настройки (.env)"}

    start_bat = PROJECT_ROOT / "start.bat"
    venv_python = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"

    try:
        if sys.platform == "win32" and start_bat.exists():
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "tg-chat-monitor", str(start_bat)],
                cwd=PROJECT_ROOT,
            )
        elif venv_python.exists():
            subprocess.Popen(
                [str(venv_python), "main.py"],
                cwd=PROJECT_ROOT,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
            )
        else:
            subprocess.Popen([sys.executable, "main.py"], cwd=PROJECT_ROOT)
    except OSError as exc:
        return {"ok": False, "message": str(exc)}

    return {"ok": True, "message": "Бот запущен в новом окне консоли"}


class SetupWizardHandler(BaseHTTPRequestHandler):
    server_version = "tg-chat-monitor-setup/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[setup] {self.address_string()} - {format % args}")

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return

        content = file_path.read_bytes()
        content_type, _ = mimetypes.guess_type(str(file_path))
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route in ("/", "/index.html"):
            self._send_file(STATIC_DIR / "index.html")
            return

        if route.startswith("/static/"):
            relative = route.removeprefix("/static/")
            self._send_file(STATIC_DIR / relative)
            return

        if route == "/api/status":
            self._send_json(200, get_status())
            return

        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "message": "Некорректный JSON"})
            return

        if parsed.path == "/api/save":
            values = {str(k): str(v).strip() for k, v in payload.get("values", {}).items()}
            for key, default in FIELD_DEFAULTS.items():
                values.setdefault(key, default)

            errors = validate_settings(values)
            if errors:
                self._send_json(400, {"ok": False, "errors": errors})
                return

            ENV_PATH.write_text(build_env_content(values), encoding="utf-8")
            self._send_json(200, {"ok": True, "message": "Файл .env сохранён", "path": str(ENV_PATH)})
            return

        if parsed.path == "/api/install":
            self._send_json(200, install_dependencies())
            return

        if parsed.path == "/api/launch":
            self._send_json(200, launch_application())
            return

        self.send_error(404, "Not found")


def run_server(port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    server = HTTPServer(("127.0.0.1", port), SetupWizardHandler)
    url = f"http://127.0.0.1:{port}/"

    print()
    print("=" * 60)
    print("  tg-chat-monitor — мастер настройки")
    print("=" * 60)
    print()
    print(f"  Откройте в браузере: {url}")
    print("  Для остановки нажмите Ctrl+C")
    print()

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nМастер настройки остановлен.")
    finally:
        server.server_close()
