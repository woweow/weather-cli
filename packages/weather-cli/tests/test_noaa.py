from datetime import datetime
from zoneinfo import ZoneInfo

from weather_cli.adapters.noaa import NoaaApi
from weather_cli.application.errors import HttpRequestError
from weather_cli.application.ranges import resolve_time_window


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_json(self, url, *, params=None, headers=None):
        key = (url, tuple(sorted((params or {}).items())))
        self.calls.append(key)
        return self.responses[key]


class FlakyHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get_json(self, url, *, params=None, headers=None):
        key = (url, tuple(sorted((params or {}).items())))
        self.calls.append(key)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_select_station_uses_nearest_station_with_data():
    window = resolve_time_window(
        "yesterday",
        "America/Los_Angeles",
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )
    point = {"properties": {"observationStations": "https://api.weather.gov/gridpoints/SEW/125,68/stations"}}
    stations = {
        "features": [
            {
                "geometry": {"coordinates": [-122.3147, 47.54548]},
                "properties": {
                    "stationIdentifier": "KBFI",
                    "name": "Boeing Field",
                    "timeZone": "America/Los_Angeles",
                    "distance": {"value": 1000},
                },
            },
            {
                "geometry": {"coordinates": [-122.3, 47.45]},
                "properties": {
                    "stationIdentifier": "KSEA",
                    "name": "Seattle-Tacoma International Airport",
                    "timeZone": "America/Los_Angeles",
                    "distance": {"value": 2000},
                },
            },
        ]
    }
    empty = {"features": []}
    one = {"features": [{"properties": {"timestamp": "2026-03-25T01:00:00+00:00"}}]}
    responses = {
        ("https://api.weather.gov/gridpoints/SEW/125,68/stations", ()): stations,
        (
            "https://api.weather.gov/stations/KBFI/observations",
            (
                ("end", "2026-03-26T07:00:00Z"),
                ("limit", 1),
                ("start", "2026-03-25T07:00:00Z"),
            ),
        ): empty,
        (
            "https://api.weather.gov/stations/KSEA/observations",
            (
                ("end", "2026-03-26T07:00:00Z"),
                ("limit", 1),
                ("start", "2026-03-25T07:00:00Z"),
            ),
        ): one,
    }

    api = NoaaApi(FakeHttpClient(responses))
    station = api.select_station(point, window, station_override=None)

    assert station.station_id == "KSEA"
    assert station.station_name == "Seattle-Tacoma International Airport"


def test_get_station_observations_follows_cursor():
    window = resolve_time_window(
        "yesterday",
        "America/Los_Angeles",
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )
    first_page = {
        "features": [{"properties": {"timestamp": "2026-03-25T23:55:00+00:00"}}],
        "pagination": {
            "next": "https://api.weather.gov/stations/KSEA/observations?cursor=abc123"
        },
    }
    second_page = {
        "features": [{"properties": {"timestamp": "2026-03-25T23:50:00+00:00"}}],
        "pagination": {},
    }
    responses = {
        (
            "https://api.weather.gov/stations/KSEA/observations",
            (
                ("end", "2026-03-26T07:00:00Z"),
                ("limit", 500),
                ("start", "2026-03-25T07:00:00Z"),
            ),
        ): first_page,
        (
            "https://api.weather.gov/stations/KSEA/observations",
            (
                ("cursor", "abc123"),
                ("end", "2026-03-26T07:00:00Z"),
                ("limit", 500),
                ("start", "2026-03-25T07:00:00Z"),
            ),
        ): second_page,
    }

    api = NoaaApi(FakeHttpClient(responses))
    observations = api.get_station_observations("KSEA", window)

    assert len(observations) == 2


def test_get_station_selection_extracts_station_coordinates():
    responses = {
        ("https://api.weather.gov/stations/KSEA", ()): {
            "geometry": {"coordinates": [-122.3, 47.45]},
            "properties": {
                "stationIdentifier": "KSEA",
                "name": "Seattle-Tacoma International Airport",
                "timeZone": "America/Los_Angeles",
            },
        }
    }

    api = NoaaApi(FakeHttpClient(responses))
    station = api.get_station_selection("KSEA")

    assert station.station_id == "KSEA"
    assert station.latitude == 47.45
    assert station.longitude == -122.3


def test_get_hourly_forecast_retries_transient_http_errors():
    http_client = FlakyHttpClient(
        [
            HttpRequestError("HTTP 503 for https://api.weather.gov/gridpoints/SEW/124,60/forecast/hourly: busy"),
            {"properties": {"periods": [{"startTime": "2026-03-26T13:00:00-07:00"}]}},
        ]
    )

    api = NoaaApi(http_client, retry_attempts=1, retry_backoff_seconds=0)
    periods = api.get_hourly_forecast("https://api.weather.gov/gridpoints/SEW/124,60/forecast/hourly")

    assert len(periods) == 1
    assert len(http_client.calls) == 2


def test_get_hourly_forecast_does_not_retry_non_transient_http_errors():
    http_client = FlakyHttpClient(
        [
            HttpRequestError(
                "HTTP 404 for https://api.weather.gov/gridpoints/SEW/124,60/forecast/hourly: not found"
            )
        ]
    )

    api = NoaaApi(http_client, retry_attempts=2, retry_backoff_seconds=0)

    try:
        api.get_hourly_forecast("https://api.weather.gov/gridpoints/SEW/124,60/forecast/hourly")
    except HttpRequestError as exc:
        assert "HTTP 404" in str(exc)
    else:
        raise AssertionError("Expected HttpRequestError")

    assert len(http_client.calls) == 1
