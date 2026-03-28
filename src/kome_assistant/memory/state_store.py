from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS timers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    minutes INTEGER NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.commit()

    def add_timer(self, minutes: int) -> int:
        created_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO timers (minutes, created_at_utc, active) VALUES (?, ?, 1)",
                (minutes, created_at),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_active_timers(self) -> list[dict[str, int | str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, minutes, created_at_utc FROM timers WHERE active = 1 ORDER BY id DESC LIMIT 20"
            ).fetchall()
        return [
            {
                "id": int(row[0]),
                "minutes": int(row[1]),
                "created_at_utc": str(row[2]),
            }
            for row in rows
        ]
