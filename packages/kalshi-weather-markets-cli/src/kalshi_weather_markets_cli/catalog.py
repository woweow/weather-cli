from __future__ import annotations

from collections import defaultdict

from kalshi_weather_markets_cli.models import CitySeriesCandidate


DOCUMENTED_CITIES = (
    "Atlanta",
    "Austin",
    "Boston",
    "Chicago",
    "Dallas",
    "Denver",
    "Houston",
    "Las Vegas",
    "Los Angeles",
    "Miami",
    "Minneapolis",
    "New Orleans",
    "NYC",
    "Oklahoma City",
    "Philadelphia",
    "Phoenix",
    "San Antonio",
    "San Francisco",
    "Seattle",
    "Washington DC",
)

CITY_PREFIXES = (
    "Highest temperature in ",
    "Daily High Temperature ",
)

CITY_SUFFIXES = (
    " Maximum Temperature Daily",
    " High Temperature Daily",
    " Maximum Daily Temperature",
    " Daily High Temperature",
    " Daily Maximum Temperature",
    " Maximum High Temperature",
    " Max Daily Temperature",
    " Max Temperature",
    " Max temp Daily",
    " Daily Max Temp",
    " Maximum Temperature",
)


def documented_cities_help_text() -> str:
    return ", ".join(DOCUMENTED_CITIES)


def build_city_catalog(series_items: list[dict]) -> dict[str, list[CitySeriesCandidate]]:
    catalog: dict[str, list[CitySeriesCandidate]] = defaultdict(list)
    for item in series_items:
        if not is_supported_temperature_series(item):
            continue
        city = extract_city_name(item["title"])
        if city is None:
            continue
        catalog[city].append(
            CitySeriesCandidate(
                city=city,
                series_ticker=item["ticker"],
                title=item["title"],
                last_updated_ts=item.get("last_updated_ts") or "",
            )
        )
    for city in catalog:
        catalog[city].sort(
            key=lambda candidate: (candidate.last_updated_ts, candidate.series_ticker),
            reverse=True,
        )
    return dict(catalog)


def extract_city_name(title: str) -> str | None:
    if title == "Highest temperature in cities":
        return None
    for prefix in CITY_PREFIXES:
        if title.startswith(prefix):
            return title.removeprefix(prefix).strip()
    for suffix in CITY_SUFFIXES:
        if title.endswith(suffix):
            return title[: -len(suffix)].strip()
    return None


def is_supported_temperature_series(item: dict) -> bool:
    title = item.get("title")
    ticker = item.get("ticker")
    if not isinstance(title, str) or not isinstance(ticker, str):
        return False
    if item.get("category") != "Climate and Weather":
        return False
    if item.get("frequency") != "daily":
        return False
    tags = item.get("tags") or []
    if "Daily temperature" not in tags:
        return False
    if not ticker.startswith("KX"):
        return False
    if title.lower().startswith("lowest"):
        return False
    return extract_city_name(title) is not None
