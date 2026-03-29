from __future__ import annotations

import json
import sqlite3
from typing import Any

from weather_study_cli.application.raw_schema import StudyCapture


def upsert_raw_capture(connection: sqlite3.Connection, capture: StudyCapture) -> int:
    capture_key = build_capture_key(capture)
    connection.execute(
        """
        INSERT INTO raw_captures (
            capture_key,
            schema_version,
            captured_at_utc,
            collector_name,
            collector_version,
            city,
            state,
            place,
            timezone,
            local_timestamp,
            local_date,
            local_hour,
            weather_source,
            weather_payload_present,
            market_source,
            market_payload_present,
            error_count,
            source_path,
            capture_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(capture_key) DO UPDATE SET
            schema_version = excluded.schema_version,
            captured_at_utc = excluded.captured_at_utc,
            collector_name = excluded.collector_name,
            collector_version = excluded.collector_version,
            city = excluded.city,
            state = excluded.state,
            place = excluded.place,
            timezone = excluded.timezone,
            local_timestamp = excluded.local_timestamp,
            local_date = excluded.local_date,
            local_hour = excluded.local_hour,
            weather_source = excluded.weather_source,
            weather_payload_present = excluded.weather_payload_present,
            market_source = excluded.market_source,
            market_payload_present = excluded.market_payload_present,
            error_count = excluded.error_count,
            source_path = excluded.source_path,
            capture_json = excluded.capture_json
        """,
        (
            capture_key,
            capture.schema_version,
            capture.captured_at_utc,
            capture.collector_name,
            capture.collector_version,
            capture.city_name,
            capture.state_code,
            capture.place,
            capture.timezone,
            capture.local_timestamp,
            capture.local_date,
            capture.local_hour,
            capture.weather.source,
            int(capture.has_weather),
            capture.market.source,
            int(capture.has_market),
            len(capture.errors),
            str(capture.source_path) if capture.source_path else None,
            json.dumps(capture.to_dict(), indent=2),
        ),
    )
    row = connection.execute(
        "SELECT id FROM raw_captures WHERE capture_key = ?",
        (capture_key,),
    ).fetchone()
    return int(row["id"])


def replace_capture_rows(connection: sqlite3.Connection, capture_id: int, capture: StudyCapture) -> None:
    connection.execute("DELETE FROM forecast_periods WHERE raw_capture_id = ?", (capture_id,))
    connection.execute("DELETE FROM market_rows WHERE raw_capture_id = ?", (capture_id,))

    weather_periods = capture.weather.payload.get("periods", []) if capture.weather.payload else []
    for index, period in enumerate(weather_periods):
        connection.execute(
            """
            INSERT INTO forecast_periods (
                raw_capture_id,
                period_index,
                start,
                end,
                temperature_f,
                relative_humidity_pct,
                precipitation_probability_pct,
                wind_speed,
                wind_direction,
                summary,
                is_daytime
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capture_id,
                index,
                period["start"],
                period["end"],
                period.get("temperature_f"),
                period.get("relative_humidity_pct"),
                period.get("precipitation_probability_pct"),
                period.get("wind_speed"),
                period.get("wind_direction"),
                period.get("summary"),
                _coerce_bool(period.get("is_daytime")),
            ),
        )

    market_rows = capture.market.payload.get("markets", []) if capture.market.payload else []
    for index, row in enumerate(market_rows):
        connection.execute(
            """
            INSERT INTO market_rows (
                raw_capture_id,
                market_index,
                provider_market_ticker,
                market_title,
                market_label,
                yes_bid_cents,
                yes_ask_cents,
                no_bid_cents,
                no_ask_cents,
                last_price_cents,
                sort_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capture_id,
                index,
                row["ticker"],
                row.get("title"),
                row["label"],
                row.get("yes_bid_cents"),
                row.get("yes_ask_cents"),
                row.get("no_bid_cents"),
                row.get("no_ask_cents"),
                row.get("last_price_cents"),
                row.get("sort_key"),
            ),
        )


def get_table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    tables = (
        "raw_captures",
        "forecast_periods",
        "market_rows",
        "daily_actuals",
        "hourly_accuracy_metrics",
        "hourly_market_opportunity_metrics",
    )
    counts: dict[str, int] = {}
    for table in tables:
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        counts[table] = int(row["count"])
    return counts


def build_capture_key(capture: StudyCapture) -> str:
    return "|".join(
        (
            capture.place,
            capture.local_date,
            f"{capture.local_hour:02d}",
            capture.captured_at_utc,
        )
    )


def _coerce_bool(value: Any) -> int | None:
    if value is None:
        return None
    return int(bool(value))
