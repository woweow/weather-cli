from __future__ import annotations

import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from weather_bets.domain.errors import SnapshotValidationError
from weather_bets.domain.simulator import normalize_optional_usd_string, parse_usd_to_cents


DEFAULT_SCHEMA_VERSION = "2"


def load_dashboard_snapshot(input_path: str | None) -> dict[str, Any]:
    if input_path:
        raw = Path(input_path).read_text(encoding="utf-8")
        source = input_path
    else:
        if sys.stdin.isatty():
            raise SnapshotValidationError(
                "No dashboard JSON provided. Use --input <path> or pipe JSON to stdin."
            )
        raw = sys.stdin.read()
        source = "stdin"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SnapshotValidationError(f"Invalid JSON from {source}: {exc.msg}") from exc
    return normalize_dashboard_snapshot(payload)


def normalize_dashboard_snapshot(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SnapshotValidationError("Dashboard payload must be a JSON object.")

    normalized = copy.deepcopy(payload)
    normalized.setdefault("schema_version", DEFAULT_SCHEMA_VERSION)
    if normalized["schema_version"] != DEFAULT_SCHEMA_VERSION:
        raise SnapshotValidationError(
            f"Dashboard payload must use schema_version {DEFAULT_SCHEMA_VERSION!r}."
        )
    _require_iso_date(normalized, "dashboard_date")
    _require_optional_str(normalized, "generated_at")
    _require_cards(normalized)
    return normalized


def extract_selected_bets(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    selections: list[dict[str, Any]] = []
    for card_index, card in enumerate(snapshot["cards"]):
        market = card["market"]
        for row_index, row in enumerate(market["rows"]):
            if row["selected_yes"]:
                selections.append(_build_selection(card_index, row_index, card, market, row, "yes"))
            if row["selected_no"]:
                selections.append(_build_selection(card_index, row_index, card, market, row, "no"))
    return selections


def _build_selection(
    card_index: int,
    row_index: int,
    card: dict[str, Any],
    market: dict[str, Any],
    row: dict[str, Any],
    side: str,
) -> dict[str, Any]:
    stake_key = f"{side}_stake_usd"
    stake_cents = parse_usd_to_cents(row[stake_key], field_name=stake_key) if row.get(stake_key) else None
    entry_price_cents = row.get("yes_ask_cents") if side == "yes" else row.get("no_ask_cents")
    return {
        "card_index": card_index,
        "row_index": row_index,
        "city": card["city"],
        "state": card["state"],
        "timezone": card["timezone"],
        "provider": market["provider"],
        "provider_series_ticker": market["provider_series_ticker"],
        "provider_event_ticker": market["provider_event_ticker"],
        "event_date": market["event_date"],
        "series_title": market["series_title"],
        "event_date_label": market["event_date_label"],
        "provider_market_ticker": row["provider_market_ticker"],
        "market_label": row["label"],
        "side": side,
        "stake_cents": stake_cents,
        "entry_price_cents": entry_price_cents,
        "last_price_cents": row.get("last_price_cents"),
        "yes_bid_cents": row.get("yes_bid_cents"),
        "yes_ask_cents": row.get("yes_ask_cents"),
        "no_bid_cents": row.get("no_bid_cents"),
        "no_ask_cents": row.get("no_ask_cents"),
    }


def _require_cards(payload: dict[str, Any]) -> None:
    cards = payload.get("cards")
    if not isinstance(cards, list) or not cards:
        raise SnapshotValidationError("Dashboard payload must include a non-empty cards list.")
    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            raise SnapshotValidationError(f"cards[{index}] must be an object.")
        _require_non_empty_str(card, "city", prefix=f"cards[{index}]")
        _require_non_empty_str(card, "state", prefix=f"cards[{index}]")
        _require_non_empty_str(card, "timezone", prefix=f"cards[{index}]")
        weather_hours = card.get("weather_hours")
        if not isinstance(weather_hours, list):
            raise SnapshotValidationError(f"cards[{index}].weather_hours must be a list.")
        for hour_index, hour in enumerate(weather_hours):
            if not isinstance(hour, dict):
                raise SnapshotValidationError(
                    f"cards[{index}].weather_hours[{hour_index}] must be an object."
                )
            prefix = f"cards[{index}].weather_hours[{hour_index}]"
            _require_non_empty_str(hour, "start", prefix=prefix)
            _require_non_empty_str(hour, "end", prefix=prefix)
            _require_number(hour, "temperature_f", prefix=prefix)
            _require_text(hour, "summary", prefix=prefix)
            _require_optional_number(hour, "precipitation_probability_pct", prefix=prefix)
            _require_optional_str(hour, "wind_speed", prefix=prefix)
        market = card.get("market")
        if not isinstance(market, dict):
            raise SnapshotValidationError(f"cards[{index}].market must be an object.")
        market_prefix = f"cards[{index}].market"
        _require_non_empty_str(market, "provider", prefix=market_prefix)
        _require_non_empty_str(market, "provider_series_ticker", prefix=market_prefix)
        _require_non_empty_str(market, "provider_event_ticker", prefix=market_prefix)
        _require_iso_date(market, "event_date", prefix=market_prefix)
        _require_non_empty_str(market, "series_title", prefix=market_prefix)
        _require_non_empty_str(market, "event_date_label", prefix=market_prefix)

        rows = market.get("rows")
        if not isinstance(rows, list) or not rows:
            raise SnapshotValidationError(f"cards[{index}].market.rows must be a non-empty list.")
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise SnapshotValidationError(
                    f"cards[{index}].market.rows[{row_index}] must be an object."
                )
            row_prefix = f"cards[{index}].market.rows[{row_index}]"
            _require_non_empty_str(row, "provider_market_ticker", prefix=row_prefix)
            _require_non_empty_str(row, "label", prefix=row_prefix)
            _require_optional_number(row, "yes_bid_cents", prefix=row_prefix)
            _require_optional_number(row, "yes_ask_cents", prefix=row_prefix)
            _require_optional_number(row, "no_bid_cents", prefix=row_prefix)
            _require_optional_number(row, "no_ask_cents", prefix=row_prefix)
            _require_optional_number(row, "last_price_cents", prefix=row_prefix)
            if "selected_yes" in row and not isinstance(row["selected_yes"], bool):
                raise SnapshotValidationError(f"{row_prefix}.selected_yes must be a boolean when present.")
            if "selected_no" in row and not isinstance(row["selected_no"], bool):
                raise SnapshotValidationError(f"{row_prefix}.selected_no must be a boolean when present.")
            row.setdefault("selected_yes", False)
            row.setdefault("selected_no", False)
            row["yes_stake_usd"] = normalize_optional_usd_string(
                row.get("yes_stake_usd"),
                field_name=f"{row_prefix}.yes_stake_usd",
            )
            row["no_stake_usd"] = normalize_optional_usd_string(
                row.get("no_stake_usd"),
                field_name=f"{row_prefix}.no_stake_usd",
            )


def _require_non_empty_str(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        raise SnapshotValidationError(f"{label} must be a non-empty string.")


def _require_text(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str):
        raise SnapshotValidationError(f"{label} must be a string.")


def _require_optional_str(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if value is not None and not isinstance(value, str):
        raise SnapshotValidationError(f"{label} must be a string when present.")


def _require_number(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, (int, float)):
        raise SnapshotValidationError(f"{label} must be a number.")


def _require_optional_number(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    value = payload.get(key)
    label = f"{prefix}.{key}" if prefix else key
    if value is not None and not isinstance(value, (int, float)):
        raise SnapshotValidationError(f"{label} must be a number when present.")


def _require_iso_date(payload: dict[str, Any], key: str, *, prefix: str | None = None) -> None:
    _require_non_empty_str(payload, key, prefix=prefix)
    label = f"{prefix}.{key}" if prefix else key
    try:
        datetime.strptime(payload[key], "%Y-%m-%d")
    except ValueError as exc:
        raise SnapshotValidationError(f"{label} must use YYYY-MM-DD format.") from exc
