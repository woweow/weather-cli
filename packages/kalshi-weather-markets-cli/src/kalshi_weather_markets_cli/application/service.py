from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from kalshi_weather_markets_cli.application.catalog import build_city_catalog
from kalshi_weather_markets_cli.application.errors import MarketDataError, UnsupportedCityError
from kalshi_weather_markets_cli.application.models import (
    CitySeriesCandidate,
    LadderSnapshot,
    MarketRange,
)


class KalshiWeatherService:
    def __init__(self, client):
        self.client = client

    def list_supported_cities(self) -> list[str]:
        catalog = build_city_catalog(self.client.list_series())
        return sorted(catalog)

    def fetch_city_ladder(self, city: str, *, target_date: str | None = None) -> LadderSnapshot:
        catalog = build_city_catalog(self.client.list_series())
        requested_city = city.strip()
        candidate_cities = [
            name for name in catalog if name.casefold() == requested_city.casefold()
        ]
        if not candidate_cities:
            supported = ", ".join(sorted(catalog))
            raise UnsupportedCityError(
                f"Unsupported city '{city}'. Use one of: {supported}"
            )
        resolved_city = candidate_cities[0]
        available_event_dates: set[str] = set()
        for candidate in catalog[resolved_city]:
            markets = self.client.get_markets(candidate.series_ticker, status="open")
            active_markets = [market for market in markets if market.get("event_ticker")]
            if not active_markets:
                continue
            available_event_dates.update(_event_dates_for_markets(active_markets))
            selected = select_active_event(active_markets, target_date=target_date)
            if selected is None:
                continue
            event_ticker, event_markets = selected
            return self._build_snapshot(candidate, event_ticker, event_markets)
        if target_date is not None and available_event_dates:
            available = ", ".join(sorted(available_event_dates))
            raise MarketDataError(
                f"No active weather markets found for {resolved_city} on {target_date}. "
                f"Available event dates: {available}"
            )
        raise MarketDataError(f"No active weather markets found for {resolved_city}")

    def _build_snapshot(
        self,
        candidate: CitySeriesCandidate,
        event_ticker: str,
        event_markets: list[dict],
    ) -> LadderSnapshot:
        ladder = sorted(
            (build_market_range(market) for market in event_markets),
            key=lambda market: market.sort_key,
        )
        return LadderSnapshot(
            provider="kalshi",
            city=candidate.city,
            series_ticker=candidate.series_ticker,
            series_title=candidate.title,
            event_ticker=event_ticker,
            event_date=format_event_date_iso(event_ticker),
            event_date_label=format_event_date(event_ticker),
            markets=ladder,
        )


def build_market_range(market: dict) -> MarketRange:
    return MarketRange(
        ticker=market["ticker"],
        title=market["title"],
        label=market.get("yes_sub_title") or market.get("no_sub_title") or market["title"],
        yes_bid_cents=dollars_to_cents(market.get("yes_bid_dollars")),
        yes_ask_cents=dollars_to_cents(market.get("yes_ask_dollars")),
        no_bid_cents=dollars_to_cents(market.get("no_bid_dollars")),
        no_ask_cents=dollars_to_cents(market.get("no_ask_dollars")),
        last_price_cents=dollars_to_cents(market.get("last_price_dollars")),
        sort_key=market_sort_key(market),
    )


def market_sort_key(market: dict) -> float:
    strike_type = market.get("strike_type")
    if strike_type == "less":
        return float((market.get("cap_strike") or 0) - 1)
    if strike_type == "between":
        return float(market.get("floor_strike") or 0)
    if strike_type == "greater":
        return float((market.get("floor_strike") or 0) + 1)
    return float("inf")


def dollars_to_cents(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(round(float(value) * 100))


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def select_active_event(
    markets: list[dict],
    *,
    target_date: str | None = None,
) -> tuple[str, list[dict]] | None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for market in markets:
        event_ticker = market.get("event_ticker")
        if not event_ticker:
            continue
        grouped[event_ticker].append(market)
    if not grouped:
        return None
    if target_date is not None:
        matching_groups = [
            (event_ticker, event_markets)
            for event_ticker, event_markets in grouped.items()
            if format_event_date_iso(event_ticker) == target_date
        ]
        if matching_groups:
            return min(
                matching_groups,
                key=lambda item: min(parse_timestamp(market["close_time"]) for market in item[1]),
            )
        return None
    return min(
        grouped.items(),
        key=lambda item: min(parse_timestamp(market["close_time"]) for market in item[1]),
    )


def format_event_date(event_ticker: str) -> str:
    date_token = event_ticker.rsplit("-", 1)[-1]
    parsed = datetime.strptime(date_token, "%y%b%d")
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"


def format_event_date_iso(event_ticker: str) -> str:
    date_token = event_ticker.rsplit("-", 1)[-1]
    parsed = datetime.strptime(date_token, "%y%b%d")
    return parsed.strftime("%Y-%m-%d")


def _event_dates_for_markets(markets: Iterable[dict]) -> set[str]:
    dates: set[str] = set()
    for market in markets:
        event_ticker = market.get("event_ticker")
        if event_ticker:
            dates.add(format_event_date_iso(event_ticker))
    return dates
