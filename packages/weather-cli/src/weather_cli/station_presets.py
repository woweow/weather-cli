from __future__ import annotations

from dataclasses import dataclass

from weather_cli.geocoding import ResolvedPlace


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().replace(",", " ").split())


@dataclass(frozen=True)
class StationPreset:
    city: str
    state_code: str
    station_id: str

    @property
    def display_place(self) -> str:
        return f"{self.city},{self.state_code}"


STATION_PRESETS: tuple[StationPreset, ...] = (
    StationPreset(city="Denver", state_code="CO", station_id="KDEN"),
    StationPreset(city="Las Vegas", state_code="NV", station_id="KLAS"),
    StationPreset(city="Los Angeles", state_code="CA", station_id="KLAX"),
    StationPreset(city="Phoenix", state_code="AZ", station_id="KPHX"),
    StationPreset(city="San Francisco", state_code="CA", station_id="KSFO"),
    StationPreset(city="Seattle", state_code="WA", station_id="KSEA"),
)

_STATION_PRESETS_BY_KEY = {
    (_normalize_name(preset.city), preset.state_code): preset.station_id
    for preset in STATION_PRESETS
}


def resolve_station_preset(place: ResolvedPlace) -> str | None:
    key = (_normalize_name(place.city), place.state_code)
    return _STATION_PRESETS_BY_KEY.get(key)


def format_station_presets_for_help() -> str:
    max_width = max(len(preset.display_place) for preset in STATION_PRESETS)
    return "\n".join(
        f"  {preset.display_place.ljust(max_width)} -> {preset.station_id}"
        for preset in STATION_PRESETS
    )
