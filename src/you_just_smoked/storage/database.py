"""SQLite connection with forward-only, numbered migrations tracked in `user_version`."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE episodes (
        id INTEGER PRIMARY KEY,
        started_at TEXT NOT NULL,
        ended_at TEXT NOT NULL,
        outcome TEXT NOT NULL,
        trigger TEXT,
        answer TEXT,
        postponed_seconds REAL
    );
    CREATE INDEX episodes_ended_at ON episodes (ended_at);
    """,
)


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the database, creating it and applying pending migrations."""
    if not isinstance(path, str):
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode = WAL")
    _migrate(connection)
    return connection


def _migrate(connection: sqlite3.Connection) -> None:
    (version,) = connection.execute("PRAGMA user_version").fetchone()
    for number, script in enumerate(_MIGRATIONS[version:], start=version + 1):
        connection.executescript(f"BEGIN; {script} PRAGMA user_version = {number}; COMMIT;")
