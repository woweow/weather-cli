from __future__ import annotations

from datetime import datetime
from typing import Any

from weather_cli.adapters.geocoding import OpenMeteoGeocoder, ResolvedPlace
from weather_cli.adapters.noaa import NoaaApi, StationSelection
from weather_cli.application.errors import DataNotFoundError
from weather_cli.application.ranges import TimeWindow, resolve_time_window
from weather_cli.application.station_presets import resolve_station_anchor, resolve_station_preset


def celsius_to_fahrenheit(value: float | None) -> float | None:
    if value is None:
        return None
    return round((value * 9 / 5) + 32, 1)


def kmh_to_mph(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value * 0.621371, 1)


def meters_to_miles(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value / 1609.344, 2)


def round_or_none(value: float | None, digits: int = 1) -> float | None:
    if value is None:
        return None
    return round(value, digits)


class WeatherService:
    def __init__(self, geocoder: OpenMeteoGeocoder, noaa_api: NoaaApi):
        self._geocoder = geocoder
        self._noaa_api = noaa_api

    def fetch(
        self,
        place: str,
        range_name: str,
        *,
        station_override: str | None = None,
        use_station_presets: bool = True,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        resolved = self._geocoder.resolve(place)
        window = resolve_time_window(range_name, resolved.timezone, now=now)

        if window.mode == "forecast":
            point, station, station_selection = self._resolve_forecast_source(
                resolved,
                station_override=station_override,
                use_station_presets=use_station_presets,
            )
            periods = self._normalize_forecast(
                self._noaa_api.get_hourly_forecast(point["properties"]["forecastHourly"]),
                window,
            )
            if not periods:
                raise DataNotFoundError(f"No NOAA forecast periods overlapped {window.name}.")
        else:
            point = self._noaa_api.get_point(resolved.latitude, resolved.longitude)
            station, station_selection = self._resolve_observation_source(
                resolved,
                point,
                window,
                station_override=station_override,
                use_station_presets=use_station_presets,
            )
            periods = self._normalize_observations(
                self._noaa_api.get_station_observations(station.station_id, window),
                window,
            )
            if not periods:
                raise DataNotFoundError(
                    f"Station {station.station_id} returned no observations inside {window.name}."
                )

        return self._build_payload(resolved, window, point, station, periods, station_selection)

    def _resolve_forecast_source(
        self,
        resolved: ResolvedPlace,
        *,
        station_override: str | None,
        use_station_presets: bool,
    ) -> tuple[dict[str, Any], StationSelection | None, str]:
        if station_override is not None:
            station = self._noaa_api.get_station_selection(station_override)
            return self._forecast_point_for_station(station), station, "override"

        if use_station_presets:
            anchor = resolve_station_anchor(resolved)
            if anchor is not None:
                station = self._noaa_api.get_station_selection(anchor.station_id)
                return self._forecast_point_for_station(station), station, "preset"

        point = self._noaa_api.get_point(resolved.latitude, resolved.longitude)
        return point, None, "forecast"

    def _resolve_observation_source(
        self,
        resolved: ResolvedPlace,
        point: dict[str, Any],
        window: TimeWindow,
        *,
        station_override: str | None,
        use_station_presets: bool,
    ) -> tuple[StationSelection, str]:
        resolved_station_override = station_override
        if resolved_station_override is not None:
            station_selection = "override"
        elif use_station_presets:
            resolved_station_override = resolve_station_preset(resolved)
            station_selection = "preset" if resolved_station_override else "nearest"
        else:
            station_selection = "nearest"

        station = self._noaa_api.select_station(point, window, resolved_station_override)
        return station, station_selection

    def _forecast_point_for_station(self, station: StationSelection) -> dict[str, Any]:
        if station.latitude is None or station.longitude is None:
            raise DataNotFoundError(
                f"Station {station.station_id} did not include coordinates for forecast lookup."
            )
        return self._noaa_api.get_point(station.latitude, station.longitude)

    def _build_payload(
        self,
        resolved: ResolvedPlace,
        window: TimeWindow,
        point: dict[str, Any],
        station: StationSelection | None,
        periods: list[dict[str, Any]],
        station_selection: str,
    ) -> dict[str, Any]:
        point_properties = point.get("properties", {})
        payload = {
            "location": {
                "input": resolved.raw_input,
                "city": resolved.city,
                "state": resolved.state_code,
                "timezone": resolved.timezone,
            },
            "resolved_coordinates": {
                "latitude": resolved.latitude,
                "longitude": resolved.longitude,
            },
            "range": {
                "name": window.name,
                "mode": window.mode,
                "start": window.start.isoformat(),
                "end": window.end.isoformat(),
            },
            "source": {
                "geocoder": "Open-Meteo geocoding",
                "provider": "NOAA weather.gov API",
                "point_url": point.get("id") or point.get("@id"),
                "station_selection": station_selection,
            },
            "station": None,
            "periods": periods,
        }

        if station is not None:
            payload["station"] = {
                "identifier": station.station_id,
                "name": station.station_name,
                "timezone": station.timezone,
                "distance_meters": station.distance_meters,
                "latitude": station.latitude,
                "longitude": station.longitude,
            }
        if window.mode == "forecast":
            payload["source"]["forecast_url"] = point_properties.get("forecastHourly")

        return payload

    def _normalize_observations(self, observations: list[dict[str, Any]], window: TimeWindow) -> list[dict[str, Any]]:
        normalized = []
        zone = window.start.tzinfo
        for observation in observations:
            properties = observation.get("properties", {})
            timestamp = datetime.fromisoformat(properties["timestamp"])
            local_timestamp = timestamp.astimezone(zone)
            if not window.contains(local_timestamp):
                continue
            normalized.append(
                {
                    "kind": "observation",
                    "start": local_timestamp.isoformat(),
                    "end": local_timestamp.isoformat(),
                    "temperature_f": celsius_to_fahrenheit(_nested_value(properties, "temperature", "value")),
                    "dewpoint_f": celsius_to_fahrenheit(_nested_value(properties, "dewpoint", "value")),
                    "relative_humidity_pct": round_or_none(_nested_value(properties, "relativeHumidity", "value")),
                    "wind_speed_mph": kmh_to_mph(_nested_value(properties, "windSpeed", "value")),
                    "wind_gust_mph": kmh_to_mph(_nested_value(properties, "windGust", "value")),
                    "wind_direction_degrees": round_or_none(_nested_value(properties, "windDirection", "value"), 0),
                    "visibility_miles": meters_to_miles(_nested_value(properties, "visibility", "value")),
                    "summary": properties.get("textDescription"),
                }
            )
        normalized.sort(key=lambda item: item["start"])
        return normalized

    def _normalize_forecast(self, periods: list[dict[str, Any]], window: TimeWindow) -> list[dict[str, Any]]:
        normalized = []
        zone = window.start.tzinfo
        for period in periods:
            start = datetime.fromisoformat(period["startTime"]).astimezone(zone)
            end = datetime.fromisoformat(period["endTime"]).astimezone(zone)
            if end <= window.start or start >= window.end:
                continue
            normalized.append(
                {
                    "kind": "forecast",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "temperature_f": round_or_none(period.get("temperature")),
                    "relative_humidity_pct": round_or_none(_nested_value(period, "relativeHumidity", "value")),
                    "precipitation_probability_pct": round_or_none(
                        _nested_value(period, "probabilityOfPrecipitation", "value")
                    ),
                    "wind_speed": period.get("windSpeed"),
                    "wind_direction": period.get("windDirection"),
                    "summary": period.get("shortForecast"),
                    "is_daytime": period.get("isDaytime"),
                }
            )
        normalized.sort(key=lambda item: item["start"])
        return normalized


def _nested_value(payload: dict[str, Any], outer_key: str, inner_key: str) -> float | None:
    outer = payload.get(outer_key) or {}
    value = outer.get(inner_key)
    if value is None:
        return None
    return float(value)
