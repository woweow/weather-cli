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


def list_daily_actual_targets(
    connection: sqlite3.Connection,
    *,
    place: str | None = None,
    local_date: str | None = None,
) -> list[dict[str, str]]:
    clauses: list[str] = []
    params: list[Any] = []
    if place is not None:
        clauses.append("place = ?")
        params.append(place)
    if local_date is not None:
        clauses.append("local_date = ?")
        params.append(local_date)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT place, local_date, timezone
        FROM raw_captures
        {where_sql}
        GROUP BY place, local_date, timezone
        ORDER BY local_date ASC, place ASC
        """,
        params,
    ).fetchall()
    return [
        {
            "place": row["place"],
            "local_date": row["local_date"],
            "timezone": row["timezone"],
        }
        for row in rows
    ]


def upsert_daily_actual(
    connection: sqlite3.Connection,
    *,
    place: str,
    local_date: str,
    timezone: str,
    observed_high_temperature_f: float,
    observed_payload: dict[str, Any],
    resolved_at_utc: str,
) -> None:
    connection.execute(
        """
        INSERT INTO daily_actuals (
            place,
            local_date,
            timezone,
            observed_high_temperature_f,
            observed_payload_json,
            resolved_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(place, local_date) DO UPDATE SET
            timezone = excluded.timezone,
            observed_high_temperature_f = excluded.observed_high_temperature_f,
            observed_payload_json = excluded.observed_payload_json,
            resolved_at_utc = excluded.resolved_at_utc
        """,
        (
            place,
            local_date,
            timezone,
            observed_high_temperature_f,
            json.dumps(observed_payload, indent=2),
            resolved_at_utc,
        ),
    )


def list_accuracy_capture_rows(
    connection: sqlite3.Connection,
    *,
    place: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if place is not None:
        clauses.append("rc.place = ?")
        params.append(place)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT
            rc.place,
            rc.timezone,
            rc.local_date,
            rc.local_hour,
            rc.captured_at_utc,
            MAX(fp.temperature_f) AS forecast_high_f
        FROM raw_captures AS rc
        LEFT JOIN forecast_periods AS fp ON fp.raw_capture_id = rc.id
        {where_sql}
        GROUP BY rc.id
        ORDER BY rc.place ASC, rc.local_date ASC, rc.local_hour ASC, rc.captured_at_utc ASC
        """,
        params,
    ).fetchall()
    return [
        {
            "place": row["place"],
            "timezone": row["timezone"],
            "local_date": row["local_date"],
            "local_hour": row["local_hour"],
            "captured_at_utc": row["captured_at_utc"],
            "forecast_high_f": row["forecast_high_f"],
        }
        for row in rows
    ]


def list_accuracy_actual_rows(
    connection: sqlite3.Connection,
    *,
    place: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if place is not None:
        clauses.append("place = ?")
        params.append(place)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT place, local_date, observed_high_temperature_f
        FROM daily_actuals
        {where_sql}
        ORDER BY place ASC, local_date ASC
        """,
        params,
    ).fetchall()
    return [
        {
            "place": row["place"],
            "local_date": row["local_date"],
            "observed_high_temperature_f": row["observed_high_temperature_f"],
        }
        for row in rows
    ]


def list_capture_hour_rows(
    connection: sqlite3.Connection,
    *,
    place: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if place is not None:
        clauses.append("place = ?")
        params.append(place)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT DISTINCT place, timezone, local_date, local_hour
        FROM raw_captures
        {where_sql}
        ORDER BY place ASC, local_date ASC, local_hour ASC
        """,
        params,
    ).fetchall()
    return [
        {
            "place": row["place"],
            "timezone": row["timezone"],
            "local_date": row["local_date"],
            "local_hour": row["local_hour"],
        }
        for row in rows
    ]


def replace_hourly_accuracy_metrics(
    connection: sqlite3.Connection,
    *,
    place: str,
    metrics: list[dict[str, Any]],
) -> None:
    connection.execute("DELETE FROM hourly_accuracy_metrics WHERE place = ?", (place,))
    for metric in metrics:
        connection.execute(
            """
            INSERT INTO hourly_accuracy_metrics (
                place,
                timezone,
                local_hour,
                valid_day_count,
                missing_day_count,
                excluded_day_count,
                correct_day_count,
                accuracy_ratio,
                computed_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric["place"],
                metric["timezone"],
                metric["local_hour"],
                metric["valid_day_count"],
                metric["missing_day_count"],
                metric["excluded_day_count"],
                metric["correct_day_count"],
                metric["accuracy_ratio"],
                metric["computed_at_utc"],
            ),
        )


def list_hourly_accuracy_metric_rows(
    connection: sqlite3.Connection,
    *,
    place: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if place is not None:
        clauses.append("place = ?")
        params.append(place)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT
            place,
            timezone,
            local_hour,
            valid_day_count,
            missing_day_count,
            excluded_day_count,
            correct_day_count,
            accuracy_ratio
        FROM hourly_accuracy_metrics
        {where_sql}
        ORDER BY place ASC, local_hour ASC
        """,
        params,
    ).fetchall()
    return [
        {
            "place": row["place"],
            "timezone": row["timezone"],
            "local_hour": row["local_hour"],
            "valid_day_count": row["valid_day_count"],
            "missing_day_count": row["missing_day_count"],
            "excluded_day_count": row["excluded_day_count"],
            "correct_day_count": row["correct_day_count"],
            "accuracy_ratio": row["accuracy_ratio"],
        }
        for row in rows
    ]


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
