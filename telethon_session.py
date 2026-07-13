"""SQLite-сессия Telethon с увеличенным timeout и WAL."""

from __future__ import annotations

import sqlite3

from telethon.sessions import SQLiteSession


class ResilientSQLiteSession(SQLiteSession):
    def _cursor(self):
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.filename,
                check_same_thread=False,
                timeout=30,
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=30000")
        return self._conn.cursor()
