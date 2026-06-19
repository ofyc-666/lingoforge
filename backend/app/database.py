from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from app.config import Settings, load_settings


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(database_path: str | Path | None = None) -> sqlite3.Connection:
    settings = load_settings()
    db_path = Path(database_path or settings.database_path)
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database(database_path: str | Path | None = None) -> None:
    with closing(connect(database_path)) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.commit()


def reset_database(database_path: str | Path | None = None) -> None:
    settings = load_settings()
    db_path = Path(database_path or settings.database_path)
    if str(db_path) != ":memory:":
        for path in (db_path, Path(f"{db_path}-journal"), Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
            if path.exists():
                path.unlink()
    init_database(db_path)


def database_is_initialized(settings: Settings | None = None) -> bool:
    settings = settings or load_settings()
    db_path = Path(settings.database_path)
    if str(db_path) != ":memory:" and not db_path.exists():
        return False

    try:
        with closing(connect(db_path)) as connection:
            row = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users'"
            ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False
