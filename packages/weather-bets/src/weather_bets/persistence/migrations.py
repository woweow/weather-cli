from __future__ import annotations

import sqlite3
from pathlib import Path

from weather_bets.domain.errors import IncompatibleDatabaseError


SCHEMA_VERSION = 2

CREATE_SCHEMA_SQL = """
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
    provider TEXT NOT NULL,
    provider_series_ticker TEXT NOT NULL,
    provider_event_ticker TEXT NOT NULL,
    provider_market_ticker TEXT NOT NULL,
    event_date TEXT NOT NULL,
    series_title TEXT NOT NULL,
    event_date_label TEXT NOT NULL,
    market_label TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('yes', 'no')),
    stake_cents INTEGER,
    entry_price_cents INTEGER,
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
    outcome_status TEXT NOT NULL CHECK (outcome_status IN ('won', 'lost', 'void')),
    resolved_at TEXT NOT NULL,
    provider_status TEXT,
    provider_result TEXT,
    provider_settlement_value_cents INTEGER,
    provider_close_time TEXT,
    observed_high_temperature_f REAL,
    simulated_contract_count TEXT,
    simulated_gross_payout_cents INTEGER,
    simulated_net_pnl_cents INTEGER,
    notes TEXT
);
"""


def initialize_schema(connection: sqlite3.Connection) -> int:
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if current_version == SCHEMA_VERSION:
        return current_version
    if current_version not in (0,):
        raise IncompatibleDatabaseError(
            f"SQLite journal schema version {current_version} is incompatible. "
            "Run `weather-bets init --reset` to recreate the database."
        )
    connection.executescript(CREATE_SCHEMA_SQL)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()
    return SCHEMA_VERSION


def reset_database_file(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
