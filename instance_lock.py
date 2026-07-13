"""Блокировка единственного экземпляра приложения."""

from __future__ import annotations

import atexit
import sys
from pathlib import Path

_lock_handle = None


def acquire_single_instance_lock(project_root: Path) -> None:
    global _lock_handle

    lock_path = project_root / ".tg-chat-monitor.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    handle = open(lock_path, "w", encoding="utf-8")

    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        print()
        print("=" * 60)
        print("  Бот уже запущен в другом окне")
        print("=" * 60)
        print()
        print("  Закройте предыдущее окно с tg-chat-monitor")
        print("  или завершите процесс python.exe в диспетчере задач.")
        print()
        print(f"  Детали: {exc}")
        print()
        sys.exit(1)

    handle.write(str(lock_path))
    handle.flush()
    _lock_handle = handle
    atexit.register(release_single_instance_lock)


def release_single_instance_lock() -> None:
    global _lock_handle

    if _lock_handle is None:
        return

    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        _lock_handle.close()
        _lock_handle = None
