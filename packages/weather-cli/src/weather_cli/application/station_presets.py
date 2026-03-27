from __future__ import annotations

from dataclasses import dataclass

from weather_cli.adapters.geocoding import ResolvedPlace


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().replace(",", " ").split())


@dataclass(frozen=True)
class CityWeatherAnchor:
    city: str
    state_code: str
    station_id: str

    @property
    def display_place(self) -> str:
        return f"{self.city},{self.state_code}"


CITY_WEATHER_ANCHORS: tuple[CityWeatherAnchor, ...] = (
    CityWeatherAnchor(city="Denver", state_code="CO", station_id="KDEN"),
    CityWeatherAnchor(city="Las Vegas", state_code="NV", station_id="KLAS"),
    CityWeatherAnchor(city="Los Angeles", state_code="CA", station_id="KLAX"),
    CityWeatherAnchor(city="Phoenix", state_code="AZ", station_id="KPHX"),
    CityWeatherAnchor(city="San Francisco", state_code="CA", station_id="KSFO"),
    CityWeatherAnchor(city="Seattle", state_code="WA", station_id="KSEA"),
)

_CITY_WEATHER_ANCHORS_BY_KEY = {
    (_normalize_name(anchor.city), anchor.state_code): anchor
    for anchor in CITY_WEATHER_ANCHORS
}


def resolve_station_anchor(place: ResolvedPlace) -> CityWeatherAnchor | None:
    key = (_normalize_name(place.city), place.state_code)
    return _CITY_WEATHER_ANCHORS_BY_KEY.get(key)


def resolve_station_preset(place: ResolvedPlace) -> str | None:
    anchor = resolve_station_anchor(place)
    if anchor is None:
        return None
    return anchor.station_id


def format_station_presets_for_help() -> str:
    max_width = max(len(anchor.display_place) for anchor in CITY_WEATHER_ANCHORS)
    return "\n".join(
        f"  {anchor.display_place.ljust(max_width)} -> {anchor.station_id}"
        for anchor in CITY_WEATHER_ANCHORS
    )
