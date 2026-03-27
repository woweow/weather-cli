from __future__ import annotations

import sqlite3


MIGRATIONS = {
    1: """
        CREATE TABLE IF NOT EXISTS decision_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            saved_at TEXT NOT NULL,
            dashboard_date TEXT NOT NULL,
            generated_at TEXT,
            snapshot_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bet_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_session_id INTEGER NOT NULL REFERENCES decision_sessions(id) ON DELETE CASCADE,
            card_index INTEGER NOT NULL,
            row_index INTEGER NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            timezone TEXT NOT NULL,
            series_title TEXT NOT NULL,
            event_ticker TEXT NOT NULL,
            event_date_label TEXT NOT NULL,
            market_label TEXT NOT NULL,
            side TEXT NOT NULL CHECK (side IN ('yes', 'no')),
            last_price_cents INTEGER,
            yes_bid_cents INTEGER,
            yes_ask_cents INTEGER,
            no_bid_cents INTEGER,
            no_ask_cents INTEGER,
            UNIQUE(decision_session_id, card_index, row_index, side)
        );

        CREATE TABLE IF NOT EXISTS bet_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bet_selection_id INTEGER NOT NULL UNIQUE REFERENCES bet_selections(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK (status IN ('won', 'lost', 'void')),
            resolved_at TEXT NOT NULL,
            actual_temperature_f REAL,
            payout_cents INTEGER,
            notes TEXT
        );
    """
}


def apply_migrations(connection: sqlite3.Connection) -> int:
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    latest_version = max(MIGRATIONS)
    if current_version >= latest_version:
        return current_version
    for version in sorted(MIGRATIONS):
        if version <= current_version:
            continue
        connection.executescript(MIGRATIONS[version])
        connection.execute(f"PRAGMA user_version = {version}")
    connection.commit()
    return latest_version
