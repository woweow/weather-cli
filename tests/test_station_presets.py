from weather_cli.geocoding import ResolvedPlace
from weather_cli.station_presets import resolve_station_preset


def test_los_angeles_defaults_to_klax():
    place = ResolvedPlace(
        raw_input="Los Angeles,CA",
        city="Los Angeles",
        state_code="CA",
        state_name="California",
        latitude=34.05223,
        longitude=-118.24368,
        timezone="America/Los_Angeles",
    )

    assert resolve_station_preset(place) == "KLAX"


def test_seattle_defaults_to_ksea():
    place = ResolvedPlace(
        raw_input="Seattle,WA",
        city="Seattle",
        state_code="WA",
        state_name="Washington",
        latitude=47.60621,
        longitude=-122.33207,
        timezone="America/Los_Angeles",
    )

    assert resolve_station_preset(place) == "KSEA"


def test_other_cities_do_not_get_a_preset():
    place = ResolvedPlace(
        raw_input="Portland,OR",
        city="Portland",
        state_code="OR",
        state_name="Oregon",
        latitude=45.52306,
        longitude=-122.67648,
        timezone="America/Los_Angeles",
    )

    assert resolve_station_preset(place) is None
