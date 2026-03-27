from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from weather_cli.errors import GeocodingError, InputError
from weather_cli.http import JsonHttpClient
from weather_cli.states import resolve_state


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


@dataclass(frozen=True)
class ResolvedPlace:
    raw_input: str
    city: str
    state_code: str
    state_name: str
    latitude: float
    longitude: float
    timezone: str


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().replace(",", " ").split())


def parse_place(raw_place: str) -> tuple[str, str, str]:
    parts = [part.strip() for part in raw_place.split(",")]
    if len(parts) != 2 or not all(parts):
        raise InputError("Place must be in strict city,state format, for example 'Seattle,WA'.")
    city, state = parts
    resolved = resolve_state(state)
    if resolved is None:
        raise InputError(f"Unsupported state value: {state!r}")
    state_code, state_name = resolved
    return city, state_code, state_name


class OpenMeteoGeocoder:
    def __init__(self, http_client: JsonHttpClient):
        self._http_client = http_client

    def resolve(self, raw_place: str) -> ResolvedPlace:
        city, state_code, state_name = parse_place(raw_place)
        params = {
            "name": city,
            "count": 10,
            "language": "en",
            "format": "json",
        }
        data = self._http_client.get_json(GEOCODING_URL, params=params)
        results = data.get("results") or []

        city_key = _normalize_name(city)
        state_key = _normalize_name(state_name)

        matches = []
        for result in results:
            if result.get("country_code") != "US":
                continue
            if _normalize_name(result.get("admin1", "")) != state_key:
                continue
            if _normalize_name(result.get("name", "")) != city_key:
                continue
            matches.append(result)

        if not matches:
            query = urlencode({"name": city, "state": state_code})
            raise GeocodingError(
                f"Could not resolve {raw_place!r} to a U.S. city/state match via Open-Meteo ({query})."
            )

        match = sorted(matches, key=lambda item: item.get("population", 0), reverse=True)[0]
        timezone = match.get("timezone")
        if not timezone:
            raise GeocodingError(f"Geocoder resolved {raw_place!r} without a timezone.")

        return ResolvedPlace(
            raw_input=raw_place,
            city=match["name"],
            state_code=state_code,
            state_name=state_name,
            latitude=float(match["latitude"]),
            longitude=float(match["longitude"]),
            timezone=timezone,
        )
