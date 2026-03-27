import pytest

from weather_cli.adapters.geocoding import OpenMeteoGeocoder, parse_place
from weather_cli.adapters.http import JsonHttpClient


class FakeHttpClient(JsonHttpClient):
    def __init__(self, payload):
        self.payload = payload

    def get_json(self, url, *, params=None, headers=None):
        return self.payload


def test_parse_place_accepts_city_and_state_code():
    city, state_code, state_name = parse_place("Seattle, WA")
    assert city == "Seattle"
    assert state_code == "WA"
    assert state_name == "Washington"


def test_parse_place_rejects_missing_state():
    with pytest.raises(Exception):
        parse_place("Seattle")


def test_geocoder_filters_by_state_and_city():
    payload = {
        "results": [
            {
                "name": "Seattle",
                "admin1": "Washington",
                "country_code": "US",
                "latitude": 47.60621,
                "longitude": -122.33207,
                "timezone": "America/Los_Angeles",
                "population": 737015,
            },
            {
                "name": "Seattle",
                "admin1": "Florida",
                "country_code": "US",
                "latitude": 25.0,
                "longitude": -80.0,
                "timezone": "America/New_York",
                "population": 10,
            },
        ]
    }
    geocoder = OpenMeteoGeocoder(FakeHttpClient(payload))

    resolved = geocoder.resolve("Seattle,WA")

    assert resolved.city == "Seattle"
    assert resolved.state_code == "WA"
    assert resolved.latitude == 47.60621
