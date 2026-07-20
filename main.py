import asyncio
import logging
import sys

from app_paths import env_path, get_project_root
from instance_lock import acquire_single_instance_lock, release_single_instance_lock
from runtime import run_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _ensure_env_exists() -> None:
    if env_path().exists():
        return

    print()
    print("=" * 60)
    print("  Файл .env не найден")
    print("=" * 60)
    print()
    print("  Запустите мастер настройки:")
    print("    python setup.py")
    print()
    print("  Или вручную скопируйте шаблон:")
    print("    cp .env.example .env   (Linux/macOS)")
    print("    copy .env.example .env   (Windows)")
    print()
    sys.exit(1)


async def main() -> None:
    await run_app(release_lock=release_single_instance_lock)


if __name__ == "__main__":
    _ensure_env_exists()
    acquire_single_instance_lock(get_project_root())
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
