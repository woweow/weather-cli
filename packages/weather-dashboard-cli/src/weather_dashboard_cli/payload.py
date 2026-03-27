from __future__ import annotations

import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from weather_dashboard_cli.errors import PayloadValidationError


DEFAULT_SCHEMA_VERSION = "1"


def load_dashboard_payload(input_path: str | None) -> dict[str, Any]:
    if input_path:
        raw = Path(input_path).read_text(encoding="utf-8")
        source = input_path
    else:
        if sys.stdin.isatty():
            raise PayloadValidationError(
                "No dashboard JSON provided. Use --input <path> or pipe JSON to stdin."
            )
        raw = sys.stdin.read()
        source = "stdin"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PayloadValidationError(f"Invalid JSON from {source}: {exc.msg}") from exc
    return normalize_dashboard_payload(payload)


def normalize_dashboard_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PayloadValidationError("Dashboard payload must be a JSON object.")

    normalized = copy.deepcopy(payload)
    normalized.setdefault("schema_version", DEFAULT_SCHEMA_VERSION)
    _require_str(normalized, "schema_version")
    _require_iso_date(normalized, "dashboard_date")
    _require_cards(normalized)
    return normalized


def dashboard_file_name(payload: dict[str, Any]) -> str:
    parsed = datetime.strptime(payload["dashboard_date"], "%Y-%m-%d")
    return parsed.strftime("%d_%m_%Y_bets_placed.json")


def build_saved_snapshot(payload: dict[str, Any], saved_at: str) -> dict[str, Any]:
    snapshot = copy.deepcopy(payload)
    snapshot["saved_at"] = saved_at
    return snapshot


def _require_cards(payload: dict[str, Any]) -> None:
    cards = payload.get("cards")
    if not isinstance(cards, list) or not cards:
        raise PayloadValidationError("Dashboard payload must include a non-empty cards list.")
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            raise PayloadValidationError(f"cards[{index}] must be an object.")
        _require_str(card, "city", prefix=f"cards[{index}]")
        _require_str(card, "state", prefix=f"cards[{index}]")
        _require_str(card, "timezone", prefix=f"cards[{index}]")
        weather_hours = card.get("weather_hours")
        if not isinstance(weather_hours, list):
            raise PayloadValidationError(f"cards[{index}].weather_hours must be a list.")
        for hour_index, hour in enumerate(weather_hours):
            if not isinstance(hour, dict):
                raise PayloadValidationError(
                    f"cards[{index}].weather_hours[{hour_index}] must be an object."
                )
            _require_str(hour, "start", prefix=f"cards[{index}].weather_hours[{hour_index}]")
            _require_str(hour, "end", prefix=f"cards[{index}].weather_hours[{hour_index}]")
            _require_number(hour, "temperature_f", prefix=f"cards[{index}].weather_hours[{hour_index}]")
            _require_str(hour, "summary", prefix=f"cards[{index}].weather_hours[{hour_index}]")
            _require_optional_number(
                hour,
                "precipitation_probability_pct",
                prefix=f"cards[{index}].weather_hours[{hour_index}]",
            )
            _require_optional_str(
                hour,
                "wind_speed",
                prefix=f"cards[{index}].weather_hours[{hour_index}]",
            )
        market = card.get("market")
        if not isinstance(market, dict):
            raise PayloadValidationError(f"cards[{index}].market must be an object.")
        _require_str(market, "series_title", prefix=f"cards[{index}].market")
        _require_str(market, "event_ticker", prefix=f"cards[{index}].market")
        _require_str(market, "event_date_label", prefix=f"cards[{index}].market")
        rows = market.get("rows")
        if not isinstance(rows, list) or not rows:
            raise PayloadValidationError(f"cards[{index}].market.rows must be a non-empty list.")
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise PayloadValidationError(
                    f"cards[{index}].market.rows[{row_index}] must be an object."
                )
            row_prefix = f"cards[{index}].market.rows[{row_index}]"
            _require_str(row, "label", prefix=row_prefix)
            _require_optional_str_or_number(row, "chance_display", prefix=row_prefix)
            _require_optional_number(row, "yes_bid_cents", prefix=row_prefix)
            _require_optional_number(row, "yes_ask_cents", prefix=row_prefix)
            _require_optional_number(row, "no_bid_cents", prefix=row_prefix)
            _require_optional_number(row, "no_ask_cents", prefix=row_prefix)
            _require_optional_number(row, "last_price_cents", prefix=row_prefix)
            if "selected_yes" in row and not isinstance(row["selected_yes"], bool):
                raise PayloadValidationError(f"{row_prefix}.selected_yes must be a boolean when present.")
            if "selected_no" in row and not isinstance(row["selected_no"], bool):
                raise PayloadValidationError(f"{row_prefix}.selected_no must be a boolean when present.")
            row.setdefault("selected_yes", False)
            row.setdefault("selected_no", False)


def _require_str(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        raise PayloadValidationError(f"{label} must be a non-empty string.")


def _require_optional_str(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if value is not None and not isinstance(value, str):
        raise PayloadValidationError(f"{label} must be a string when present.")


def _require_number(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, (int, float)):
        raise PayloadValidationError(f"{label} must be a number.")


def _require_optional_number(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if value is not None and not isinstance(value, (int, float)):
        raise PayloadValidationError(f"{label} must be a number when present.")


def _require_optional_str_or_number(
    payload: dict[str, Any], key: str, *, prefix: str | None = None
) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if value is not None and not isinstance(value, (str, int, float)):
        raise PayloadValidationError(f"{label} must be a string or number when present.")


def _require_iso_date(payload: dict[str, Any], key: str) -> None:
    _require_str(payload, key)
    try:
        datetime.strptime(payload[key], "%Y-%m-%d")
    except ValueError as exc:
        raise PayloadValidationError(f"{key} must use YYYY-MM-DD format.") from exc
