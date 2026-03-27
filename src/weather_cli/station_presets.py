from __future__ import annotations

from weather_cli.geocoding import ResolvedPlace


STATION_PRESETS = {
    ("los angeles", "CA"): "KLAX",
    ("seattle", "WA"): "KSEA",
}


def resolve_station_preset(place: ResolvedPlace) -> str | None:
    key = (_normalize_name(place.city), place.state_code)
    return STATION_PRESETS.get(key)


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().replace(",", " ").split())
