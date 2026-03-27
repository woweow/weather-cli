from datetime import datetime
from zoneinfo import ZoneInfo

from weather_cli.adapters.geocoding import ResolvedPlace
from weather_cli.adapters.noaa import StationSelection
from weather_cli.application.service import WeatherService


class FakeGeocoder:
    def resolve(self, place):
        return ResolvedPlace(
            raw_input=place,
            city="Seattle",
            state_code="WA",
            state_name="Washington",
            latitude=47.60621,
            longitude=-122.33207,
            timezone="America/Los_Angeles",
        )


class FakeNoaaApi:
    def __init__(self):
        self.last_station_override = None
        self.last_point_lookup = None
        self.last_forecast_url = None

    def get_point(self, latitude, longitude):
        self.last_point_lookup = (latitude, longitude)
        if (latitude, longitude) == (47.45, -122.3):
            return {
                "id": "https://api.weather.gov/points/47.45,-122.3",
                "properties": {
                    "forecastHourly": "https://api.weather.gov/gridpoints/SEW/124,60/forecast/hourly"
                },
            }
        if (latitude, longitude) == (33.93806, -118.38889):
            return {
                "id": "https://api.weather.gov/points/33.9381,-118.3889",
                "properties": {
                    "forecastHourly": "https://api.weather.gov/gridpoints/LOX/149,41/forecast/hourly"
                },
            }
        if (latitude, longitude) == (34.05223, -118.24368):
            return {
                "id": "https://api.weather.gov/points/34.0522,-118.2437",
                "properties": {
                    "forecastHourly": "https://api.weather.gov/gridpoints/LOX/155,45/forecast/hourly"
                },
            }
        return {
            "id": f"https://api.weather.gov/points/{latitude},{longitude}",
            "properties": {
                "forecastHourly": "https://api.weather.gov/gridpoints/GEN/0,0/forecast/hourly"
            },
        }

    def get_station_selection(self, station_id):
        if station_id == "KSEA":
            return StationSelection(
                station_id="KSEA",
                station_name="Seattle-Tacoma International Airport",
                timezone="America/Los_Angeles",
                distance_meters=None,
                latitude=47.45,
                longitude=-122.3,
            )
        if station_id == "KLAX":
            return StationSelection(
                station_id="KLAX",
                station_name="Los Angeles International Airport",
                timezone="America/Los_Angeles",
                distance_meters=None,
                latitude=33.93806,
                longitude=-118.38889,
            )
        if station_id == "KBFI":
            return StationSelection(
                station_id="KBFI",
                station_name="Boeing Field",
                timezone="America/Los_Angeles",
                distance_meters=None,
                latitude=47.53,
                longitude=-122.3,
            )
        raise AssertionError(f"Unexpected station lookup for {station_id}")

    def select_station(self, point, window, station_override):
        self.last_station_override = station_override
        station = self.get_station_selection(station_override or "KSEA")
        return StationSelection(
            station_id=station.station_id,
            station_name=station.station_name,
            timezone=station.timezone,
            distance_meters=2000 if station_override is None else None,
            latitude=station.latitude,
            longitude=station.longitude,
        )

    def get_station_observations(self, station_id, window):
        return [
            {
                "properties": {
                    "timestamp": "2026-03-26T18:00:00+00:00",
                    "textDescription": "Clear",
                    "temperature": {"value": 10.0},
                    "dewpoint": {"value": 2.0},
                    "relativeHumidity": {"value": 60.0},
                    "windSpeed": {"value": 10.0},
                    "windGust": {"value": None},
                    "windDirection": {"value": 180.0},
                    "visibility": {"value": 16093.44},
                }
            }
        ]

    def get_hourly_forecast(self, forecast_url):
        self.last_forecast_url = forecast_url
        return [
            {
                "startTime": "2026-03-26T13:00:00-07:00",
                "endTime": "2026-03-26T14:00:00-07:00",
                "temperature": 52,
                "relativeHumidity": {"value": 55},
                "probabilityOfPrecipitation": {"value": 0},
                "windSpeed": "5 mph",
                "windDirection": "NW",
                "shortForecast": "Sunny",
                "isDaytime": True,
            },
            {
                "startTime": "2026-03-27T14:00:00-07:00",
                "endTime": "2026-03-27T15:00:00-07:00",
                "temperature": 60,
                "relativeHumidity": {"value": 40},
                "probabilityOfPrecipitation": {"value": 0},
                "windSpeed": "8 mph",
                "windDirection": "W",
                "shortForecast": "Sunny",
                "isDaytime": True,
            },
        ]


def test_fetch_normalizes_observations():
    noaa_api = FakeNoaaApi()
    service = WeatherService(FakeGeocoder(), noaa_api)
    payload = service.fetch(
        "Seattle,WA",
        "today",
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )

    assert noaa_api.last_station_override == "KSEA"
    assert payload["station"]["identifier"] == "KSEA"
    assert payload["source"]["station_selection"] == "preset"
    assert payload["periods"][0]["temperature_f"] == 50.0
    assert payload["periods"][0]["wind_speed_mph"] == 6.2


def test_fetch_filters_forecast_window():
    noaa_api = FakeNoaaApi()
    service = WeatherService(FakeGeocoder(), noaa_api)
    payload = service.fetch(
        "Seattle,WA",
        "next-24h",
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )

    assert payload["station"]["identifier"] == "KSEA"
    assert payload["source"]["station_selection"] == "preset"
    assert payload["source"]["forecast_url"] == "https://api.weather.gov/gridpoints/SEW/124,60/forecast/hourly"
    assert noaa_api.last_point_lookup == (47.45, -122.3)
    assert len(payload["periods"]) == 1
    assert payload["periods"][0]["summary"] == "Sunny"


class RestOfTodayNoaaApi(FakeNoaaApi):
    def get_hourly_forecast(self, forecast_url):
        self.last_forecast_url = forecast_url
        return [
            {
                "startTime": "2026-03-26T12:00:00-07:00",
                "endTime": "2026-03-26T13:00:00-07:00",
                "temperature": 51,
                "relativeHumidity": {"value": 50},
                "probabilityOfPrecipitation": {"value": 0},
                "windSpeed": "5 mph",
                "windDirection": "NW",
                "shortForecast": "Sunny",
                "isDaytime": True,
            },
            {
                "startTime": "2026-03-26T23:00:00-07:00",
                "endTime": "2026-03-27T00:00:00-07:00",
                "temperature": 44,
                "relativeHumidity": {"value": 70},
                "probabilityOfPrecipitation": {"value": 5},
                "windSpeed": "4 mph",
                "windDirection": "N",
                "shortForecast": "Mostly Cloudy",
                "isDaytime": False,
            },
            {
                "startTime": "2026-03-27T00:00:00-07:00",
                "endTime": "2026-03-27T01:00:00-07:00",
                "temperature": 42,
                "relativeHumidity": {"value": 75},
                "probabilityOfPrecipitation": {"value": 5},
                "windSpeed": "3 mph",
                "windDirection": "N",
                "shortForecast": "Cloudy",
                "isDaytime": False,
            },
        ]


def test_fetch_rest_of_today_includes_current_hour_and_excludes_tomorrow():
    noaa_api = RestOfTodayNoaaApi()
    service = WeatherService(FakeGeocoder(), noaa_api)
    payload = service.fetch(
        "Seattle,WA",
        "rest-of-today",
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )

    assert payload["station"]["identifier"] == "KSEA"
    assert payload["source"]["station_selection"] == "preset"
    assert [period["start"] for period in payload["periods"]] == [
        "2026-03-26T12:00:00-07:00",
        "2026-03-26T23:00:00-07:00",
    ]


class CapturingNoaaApi(FakeNoaaApi):
    def __init__(self):
        self.last_station_override = None

    def select_station(self, point, window, station_override):
        self.last_station_override = station_override
        station_id = station_override or "FHMC1"
        station_name = "Los Angeles, Los Angeles International Airport" if station_id == "KLAX" else "LOS ANGELES DOWNTOWN"
        return StationSelection(
            station_id=station_id,
            station_name=station_name,
            timezone="America/Los_Angeles",
            distance_meters=1642 if station_id != "KLAX" else None,
            latitude=33.93806 if station_id == "KLAX" else 34.06778,
            longitude=-118.38889 if station_id == "KLAX" else -118.24167,
        )

    def get_station_observations(self, station_id, window):
        return [
            {
                "properties": {
                    "timestamp": "2026-03-25T20:00:00+00:00",
                    "textDescription": "Sunny",
                    "temperature": {"value": 20.0},
                    "dewpoint": {"value": 10.0},
                    "relativeHumidity": {"value": 50.0},
                    "windSpeed": {"value": 8.0},
                    "windGust": {"value": None},
                    "windDirection": {"value": 250.0},
                    "visibility": {"value": 16093.44},
                }
            }
        ]


class LosAngelesGeocoder:
    def resolve(self, place):
        return ResolvedPlace(
            raw_input=place,
            city="Los Angeles",
            state_code="CA",
            state_name="California",
            latitude=34.05223,
            longitude=-118.24368,
            timezone="America/Los_Angeles",
        )


def test_fetch_uses_los_angeles_station_preset_by_default():
    noaa_api = CapturingNoaaApi()
    service = WeatherService(LosAngelesGeocoder(), noaa_api)

    payload = service.fetch(
        "Los Angeles,CA",
        "yesterday",
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )

    assert noaa_api.last_station_override == "KLAX"
    assert payload["source"]["station_selection"] == "preset"


def test_fetch_can_disable_station_presets():
    noaa_api = CapturingNoaaApi()
    service = WeatherService(LosAngelesGeocoder(), noaa_api)

    payload = service.fetch(
        "Los Angeles,CA",
        "yesterday",
        use_station_presets=False,
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )

    assert noaa_api.last_station_override is None
    assert payload["source"]["station_selection"] == "nearest"


def test_fetch_forecast_can_disable_station_presets():
    noaa_api = FakeNoaaApi()
    service = WeatherService(LosAngelesGeocoder(), noaa_api)

    payload = service.fetch(
        "Los Angeles,CA",
        "next-24h",
        use_station_presets=False,
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )

    assert payload["station"] is None
    assert payload["source"]["station_selection"] == "forecast"
    assert payload["source"]["forecast_url"] == "https://api.weather.gov/gridpoints/LOX/155,45/forecast/hourly"
    assert noaa_api.last_point_lookup == (34.05223, -118.24368)


def test_fetch_forecast_can_use_station_override():
    noaa_api = FakeNoaaApi()
    service = WeatherService(FakeGeocoder(), noaa_api)

    payload = service.fetch(
        "Seattle,WA",
        "next-24h",
        station_override="KBFI",
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )

    assert payload["station"]["identifier"] == "KBFI"
    assert payload["source"]["station_selection"] == "override"
    assert noaa_api.last_point_lookup == (47.53, -122.3)


class PortlandGeocoder:
    def resolve(self, place):
        return ResolvedPlace(
            raw_input=place,
            city="Portland",
            state_code="OR",
            state_name="Oregon",
            latitude=45.52306,
            longitude=-122.67648,
            timezone="America/Los_Angeles",
        )


def test_fetch_forecast_for_non_preset_city_remains_generic():
    noaa_api = FakeNoaaApi()
    service = WeatherService(PortlandGeocoder(), noaa_api)

    payload = service.fetch(
        "Portland,OR",
        "next-24h",
        now=datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC")),
    )

    assert payload["station"] is None
    assert payload["source"]["station_selection"] == "forecast"
    assert noaa_api.last_point_lookup == (45.52306, -122.67648)
