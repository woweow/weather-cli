from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_DB_PATH = REPO_ROOT / ".study" / "weather-study.db"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


@contextmanager
def open_connection(db_path: Path):
    connection = connect(db_path)
    try:
        yield connection
    finally:
        connection.close()
