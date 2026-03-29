from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from weather_study_cli.application.errors import StudyValidationError
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import get_daily_actual_row, list_day_capture_rows


@dataclass(frozen=True)
class DayCaptureDrilldown:
    local_hour: int
    local_timestamp: str
    captured_at_utc: str
    weather_payload_present: bool
    market_payload_present: bool
    forecast_high_temperature_f: float | None
    forecast_matches_actual: bool | None
    forecast_period_count: int
    forecast_periods: tuple[dict[str, Any], ...]
    market_event_ticker: str | None
    market_row_count: int
    market_leader_label: str | None
    market_leader_last_price_cents: int | None
    market_rows: tuple[dict[str, Any], ...]
    error_sources: tuple[str, ...]
    error_messages: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "local_hour": self.local_hour,
            "local_timestamp": self.local_timestamp,
            "captured_at_utc": self.captured_at_utc,
            "weather_payload_present": self.weather_payload_present,
            "market_payload_present": self.market_payload_present,
            "forecast_high_temperature_f": self.forecast_high_temperature_f,
            "forecast_matches_actual": self.forecast_matches_actual,
            "forecast_period_count": self.forecast_period_count,
            "forecast_periods": list(self.forecast_periods),
            "market_event_ticker": self.market_event_ticker,
            "market_row_count": self.market_row_count,
            "market_leader_label": self.market_leader_label,
            "market_leader_last_price_cents": self.market_leader_last_price_cents,
            "market_rows": list(self.market_rows),
            "error_sources": list(self.error_sources),
            "error_messages": list(self.error_messages),
        }


@dataclass(frozen=True)
class StudyDayDrilldownReport:
    db_path: Path
    place: str
    timezone: str
    local_date: str
    actual_high_temperature_f: float | None
    actual_resolved_at_utc: str | None
    captures: tuple[DayCaptureDrilldown, ...]

    @property
    def capture_count(self) -> int:
        return len(self.captures)

    @property
    def correct_capture_count(self) -> int:
        return sum(1 for capture in self.captures if capture.forecast_matches_actual is True)

    def to_dict(self) -> dict[str, object]:
        return {
            "db_path": str(self.db_path),
            "place": self.place,
            "timezone": self.timezone,
            "local_date": self.local_date,
            "actual_high_temperature_f": self.actual_high_temperature_f,
            "actual_resolved_at_utc": self.actual_resolved_at_utc,
            "capture_count": self.capture_count,
            "correct_capture_count": self.correct_capture_count,
            "captures": [capture.to_dict() for capture in self.captures],
        }


def load_day_drilldown_report(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    place: str,
    local_date: str,
) -> StudyDayDrilldownReport:
    target_db_path = Path(db_path).expanduser().resolve()

    with open_connection(target_db_path) as connection:
        initialize_schema(connection)
        capture_rows = list_day_capture_rows(connection, place=place, local_date=local_date)
        actual_row = get_daily_actual_row(connection, place=place, local_date=local_date)

    if not capture_rows:
        raise StudyValidationError(
            f"No raw captures were found for {place} on {local_date}. Run `weather-study ingest-raw` first."
        )

    timezone = str(capture_rows[0]["timezone"])
    actual_high = None if actual_row is None else actual_row["observed_high_temperature_f"]
    actual_resolved_at_utc = None if actual_row is None else actual_row["resolved_at_utc"]

    captures: list[DayCaptureDrilldown] = []
    for row in capture_rows:
        payload = json.loads(str(row["capture_json"]))
        weather_payload = payload.get("weather", {}).get("payload")
        market_payload = payload.get("market", {}).get("payload")
        forecast_periods = tuple(weather_payload.get("periods", [])) if weather_payload else ()
        market_rows = tuple(market_payload.get("markets", [])) if market_payload else ()
        forecast_high = _forecast_high_temperature(forecast_periods)
        market_leader = _select_market_leader(market_rows)
        errors = tuple(payload.get("errors", []))
        captures.append(
            DayCaptureDrilldown(
                local_hour=int(row["local_hour"]),
                local_timestamp=str(row["local_timestamp"]),
                captured_at_utc=str(row["captured_at_utc"]),
                weather_payload_present=bool(row["weather_payload_present"]),
                market_payload_present=bool(row["market_payload_present"]),
                forecast_high_temperature_f=forecast_high,
                forecast_matches_actual=_forecast_matches_actual(forecast_high, actual_high),
                forecast_period_count=len(forecast_periods),
                forecast_periods=forecast_periods,
                market_event_ticker=(None if market_payload is None else market_payload.get("event_ticker")),
                market_row_count=len(market_rows),
                market_leader_label=(None if market_leader is None else market_leader.get("label")),
                market_leader_last_price_cents=(
                    None if market_leader is None else market_leader.get("last_price_cents")
                ),
                market_rows=market_rows,
                error_sources=tuple(str(item.get("source", "")) for item in errors),
                error_messages=tuple(str(item.get("message", "")) for item in errors),
            )
        )

    return StudyDayDrilldownReport(
        db_path=target_db_path,
        place=place,
        timezone=timezone,
        local_date=local_date,
        actual_high_temperature_f=actual_high,
        actual_resolved_at_utc=actual_resolved_at_utc,
        captures=tuple(captures),
    )


def _forecast_high_temperature(periods: tuple[dict[str, Any], ...]) -> float | None:
    temperatures = [period.get("temperature_f") for period in periods if period.get("temperature_f") is not None]
    if not temperatures:
        return None
    return max(float(value) for value in temperatures)


def _forecast_matches_actual(forecast_high: float | None, actual_high: float | None) -> bool | None:
    if forecast_high is None or actual_high is None:
        return None
    return _round_half_up(forecast_high) == _round_half_up(actual_high)


def _round_half_up(value: float) -> int:
    return int(value + 0.5)


def _select_market_leader(markets: tuple[dict[str, Any], ...]) -> dict[str, Any] | None:
    if not markets:
        return None
    return max(
        markets,
        key=lambda market: (
            _market_confidence_value(market),
            float(market.get("sort_key") or float("-inf")),
        ),
    )


def _market_confidence_value(market: dict[str, Any]) -> int:
    for key in ("last_price_cents", "yes_bid_cents", "yes_ask_cents"):
        value = market.get(key)
        if value is not None:
            return int(value)
    return -1
