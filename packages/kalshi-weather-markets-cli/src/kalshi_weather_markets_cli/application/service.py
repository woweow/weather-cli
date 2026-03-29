from __future__ import annotations

from collections import defaultdict
from datetime import datetime

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

    def fetch_city_ladder(self, city: str) -> LadderSnapshot:
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
        for candidate in catalog[resolved_city]:
            markets = self.client.get_markets(candidate.series_ticker, status="open")
            active_markets = [market for market in markets if market.get("event_ticker")]
            if active_markets:
                return self._build_snapshot(candidate, active_markets)
        raise MarketDataError(f"No active weather markets found for {resolved_city}")

    def _build_snapshot(
        self,
        candidate: CitySeriesCandidate,
        markets: list[dict],
    ) -> LadderSnapshot:
        grouped: dict[str, list[dict]] = defaultdict(list)
        for market in markets:
            grouped[market["event_ticker"]].append(market)
        if not grouped:
            raise MarketDataError(f"No active weather markets found for {candidate.city}")

        event_ticker, event_markets = min(
            grouped.items(),
            key=lambda item: min(parse_timestamp(market["close_time"]) for market in item[1]),
        )
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


def format_event_date(event_ticker: str) -> str:
    date_token = event_ticker.rsplit("-", 1)[-1]
    parsed = datetime.strptime(date_token, "%y%b%d")
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"


def format_event_date_iso(event_ticker: str) -> str:
    date_token = event_ticker.rsplit("-", 1)[-1]
    parsed = datetime.strptime(date_token, "%y%b%d")
    return parsed.strftime("%Y-%m-%d")
