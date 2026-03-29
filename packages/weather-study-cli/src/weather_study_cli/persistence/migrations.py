from __future__ import annotations

import sqlite3
from pathlib import Path

from weather_study_cli.application.errors import IncompatibleStudyDatabaseError


SCHEMA_VERSION = 1

CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_key TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL,
    captured_at_utc TEXT NOT NULL,
    collector_name TEXT NOT NULL,
    collector_version TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    place TEXT NOT NULL,
    timezone TEXT NOT NULL,
    local_timestamp TEXT NOT NULL,
    local_date TEXT NOT NULL,
    local_hour INTEGER NOT NULL,
    weather_source TEXT NOT NULL,
    weather_payload_present INTEGER NOT NULL CHECK (weather_payload_present IN (0, 1)),
    market_source TEXT NOT NULL,
    market_payload_present INTEGER NOT NULL CHECK (market_payload_present IN (0, 1)),
    error_count INTEGER NOT NULL,
    source_path TEXT,
    capture_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_captures_place_date_hour
    ON raw_captures(place, local_date, local_hour);

CREATE TABLE IF NOT EXISTS forecast_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_capture_id INTEGER NOT NULL REFERENCES raw_captures(id) ON DELETE CASCADE,
    period_index INTEGER NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    temperature_f REAL,
    relative_humidity_pct REAL,
    precipitation_probability_pct REAL,
    wind_speed TEXT,
    wind_direction TEXT,
    summary TEXT,
    is_daytime INTEGER,
    UNIQUE(raw_capture_id, period_index)
);

CREATE INDEX IF NOT EXISTS idx_forecast_periods_capture_start
    ON forecast_periods(raw_capture_id, start);

CREATE TABLE IF NOT EXISTS market_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_capture_id INTEGER NOT NULL REFERENCES raw_captures(id) ON DELETE CASCADE,
    market_index INTEGER NOT NULL,
    provider_market_ticker TEXT NOT NULL,
    market_title TEXT,
    market_label TEXT NOT NULL,
    yes_bid_cents INTEGER,
    yes_ask_cents INTEGER,
    no_bid_cents INTEGER,
    no_ask_cents INTEGER,
    last_price_cents INTEGER,
    sort_key REAL,
    UNIQUE(raw_capture_id, market_index)
);

CREATE INDEX IF NOT EXISTS idx_market_rows_capture_sort
    ON market_rows(raw_capture_id, sort_key);

CREATE TABLE IF NOT EXISTS daily_actuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place TEXT NOT NULL,
    local_date TEXT NOT NULL,
    timezone TEXT NOT NULL,
    observed_high_temperature_f REAL,
    observed_payload_json TEXT,
    resolved_at_utc TEXT,
    UNIQUE(place, local_date)
);

CREATE TABLE IF NOT EXISTS hourly_accuracy_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place TEXT NOT NULL,
    timezone TEXT NOT NULL,
    local_hour INTEGER NOT NULL,
    valid_day_count INTEGER NOT NULL,
    missing_day_count INTEGER NOT NULL,
    excluded_day_count INTEGER NOT NULL,
    correct_day_count INTEGER NOT NULL,
    accuracy_ratio REAL NOT NULL,
    computed_at_utc TEXT NOT NULL,
    UNIQUE(place, local_hour)
);

CREATE TABLE IF NOT EXISTS hourly_market_opportunity_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place TEXT NOT NULL,
    timezone TEXT NOT NULL,
    local_hour INTEGER NOT NULL,
    valid_day_count INTEGER NOT NULL,
    missing_day_count INTEGER NOT NULL,
    matching_market_count INTEGER NOT NULL,
    computed_at_utc TEXT NOT NULL,
    UNIQUE(place, local_hour)
);
"""


def initialize_schema(connection: sqlite3.Connection) -> int:
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if current_version == SCHEMA_VERSION:
        return current_version
    if current_version not in (0,):
        raise IncompatibleStudyDatabaseError(
            f"Study SQLite schema version {current_version} is incompatible. "
            "Run `weather-study ingest-raw --reset` to recreate the database."
        )
    connection.executescript(CREATE_SCHEMA_SQL)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()
    return SCHEMA_VERSION


def reset_database_file(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
