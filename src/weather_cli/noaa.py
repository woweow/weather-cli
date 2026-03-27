from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

from weather_cli.errors import DataNotFoundError
from weather_cli.http import JsonHttpClient
from weather_cli.ranges import TimeWindow, isoformat_utc


NOAA_API_ROOT = "https://api.weather.gov"


@dataclass(frozen=True)
class StationSelection:
    station_id: str
    station_name: str
    timezone: str | None
    distance_meters: float | None
    latitude: float | None
    longitude: float | None


class NoaaApi:
    def __init__(self, http_client: JsonHttpClient):
        self._http_client = http_client

    def get_point(self, latitude: float, longitude: float) -> dict[str, Any]:
        return self._http_client.get_json(f"{NOAA_API_ROOT}/points/{latitude},{longitude}")

    def get_hourly_forecast(self, forecast_url: str) -> list[dict[str, Any]]:
        data = self._http_client.get_json(forecast_url, params={"units": "us"})
        return data.get("properties", {}).get("periods", [])

    def get_station(self, station_id: str) -> dict[str, Any]:
        return self._http_client.get_json(f"{NOAA_API_ROOT}/stations/{station_id}")

    def get_stations_for_point(self, point: dict[str, Any]) -> list[dict[str, Any]]:
        stations_url = point["properties"]["observationStations"]
        data = self._http_client.get_json(stations_url)
        return data.get("features", [])

    def station_has_observations(self, station_id: str, window: TimeWindow) -> bool:
        data = self._http_client.get_json(
            f"{NOAA_API_ROOT}/stations/{station_id}/observations",
            params={
                "start": isoformat_utc(window.start),
                "end": isoformat_utc(window.end),
                "limit": 1,
            },
        )
        return bool(data.get("features"))

    def get_station_observations(self, station_id: str, window: TimeWindow) -> list[dict[str, Any]]:
        url = f"{NOAA_API_ROOT}/stations/{station_id}/observations"
        cursor: str | None = None
        features: list[dict[str, Any]] = []

        while True:
            params = {
                "start": isoformat_utc(window.start),
                "end": isoformat_utc(window.end),
                "limit": 500,
            }
            if cursor:
                params["cursor"] = cursor

            data = self._http_client.get_json(url, params=params)
            page_features = data.get("features", [])
            features.extend(page_features)

            next_url = data.get("pagination", {}).get("next")
            if not next_url:
                break

            cursor_values = parse_qs(urlsplit(next_url).query).get("cursor")
            if not cursor_values:
                break
            cursor = cursor_values[0]

        return features

    def select_station(self, point: dict[str, Any], window: TimeWindow, station_override: str | None) -> StationSelection:
        if station_override:
            station = self.get_station(station_override)
            if not self.station_has_observations(station_override, window):
                raise DataNotFoundError(
                    f"Station {station_override} returned no observations for {window.name}."
                )
            return self._station_selection_from_station(station)

        for feature in self.get_stations_for_point(point):
            properties = feature.get("properties", {})
            station_id = properties.get("stationIdentifier")
            if not station_id:
                continue
            if self.station_has_observations(station_id, window):
                return self._station_selection_from_feature(feature)

        place = point.get("properties", {}).get("relativeLocation", {}).get("properties", {})
        city = place.get("city", "the requested location")
        state = place.get("state", "")
        label = f"{city}, {state}".strip(", ")
        raise DataNotFoundError(f"No NOAA observation station had data for {window.name} near {label}.")

    def _station_selection_from_feature(self, feature: dict[str, Any]) -> StationSelection:
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates") or [None, None]
        return StationSelection(
            station_id=properties.get("stationIdentifier", ""),
            station_name=properties.get("name", ""),
            timezone=properties.get("timeZone"),
            distance_meters=_value_or_none(properties.get("distance", {}).get("value")),
            latitude=_value_or_none(coords[1] if len(coords) > 1 else None),
            longitude=_value_or_none(coords[0] if coords else None),
        )

    def _station_selection_from_station(self, station: dict[str, Any]) -> StationSelection:
        properties = station.get("properties", {})
        geometry = station.get("geometry", {})
        coords = geometry.get("coordinates") or [None, None]
        return StationSelection(
            station_id=properties.get("stationIdentifier", ""),
            station_name=properties.get("name", ""),
            timezone=properties.get("timeZone"),
            distance_meters=None,
            latitude=_value_or_none(coords[1] if len(coords) > 1 else None),
            longitude=_value_or_none(coords[0] if coords else None),
        )


def _value_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
