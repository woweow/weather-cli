from __future__ import annotations

import re
from typing import Any


_INTEGER_PATTERN = re.compile(r"-?\d+")


def round_half_up(value: float) -> int:
    return int(value + 0.5)


def find_winning_market_row(markets: tuple[dict[str, Any], ...], actual_high: float) -> dict[str, Any] | None:
    rounded_actual = round_half_up(actual_high)
    for market in markets:
        label = str(market.get("label") or "")
        if label_contains_temperature(label, rounded_actual):
            return market
    return None


def label_contains_temperature(label: str, temperature_f: int) -> bool:
    normalized = label.casefold()
    values = [int(value) for value in _INTEGER_PATTERN.findall(label)]
    if not values:
        return False
    if "or below" in normalized:
        return temperature_f <= values[0]
    if "or above" in normalized:
        return temperature_f >= values[0]
    if "to" in normalized and len(values) >= 2:
        return values[0] <= temperature_f <= values[1]
    return False


def select_market_leader(markets: tuple[dict[str, Any], ...]) -> dict[str, Any] | None:
    if not markets:
        return None
    return max(
        markets,
        key=lambda market: (
            market_confidence_value(market),
            float(market.get("sort_key") or float("-inf")),
        ),
    )


def market_confidence_value(market: dict[str, Any]) -> int:
    for key in ("last_price_cents", "yes_bid_cents", "yes_ask_cents"):
        value = market.get(key)
        if value is not None:
            return int(value)
    return -1
