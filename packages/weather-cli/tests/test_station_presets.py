import pytest

from weather_cli.geocoding import ResolvedPlace
from weather_cli.station_presets import format_station_presets_for_help, resolve_station_preset


@pytest.mark.parametrize(
    ("city", "state_code", "state_name", "latitude", "longitude", "station_id"),
    [
        ("Denver", "CO", "Colorado", 39.73915, -104.9847, "KDEN"),
        ("Las Vegas", "NV", "Nevada", 36.17497, -115.13722, "KLAS"),
        ("Los Angeles", "CA", "California", 34.05223, -118.24368, "KLAX"),
        ("Phoenix", "AZ", "Arizona", 33.44838, -112.07404, "KPHX"),
        ("San Francisco", "CA", "California", 37.77493, -122.41942, "KSFO"),
        ("Seattle", "WA", "Washington", 47.60621, -122.33207, "KSEA"),
    ],
)
def test_cities_with_climate_station_defaults(
    city,
    state_code,
    state_name,
    latitude,
    longitude,
    station_id,
):
    place = ResolvedPlace(
        raw_input=f"{city},{state_code}",
        city=city,
        state_code=state_code,
        state_name=state_name,
        latitude=latitude,
        longitude=longitude,
        timezone="America/Los_Angeles",
    )

    assert resolve_station_preset(place) == station_id


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


def test_help_formatter_includes_all_presets():
    help_text = format_station_presets_for_help()

    assert "Denver,CO        -> KDEN" in help_text
    assert "Las Vegas,NV     -> KLAS" in help_text
    assert "Los Angeles,CA   -> KLAX" in help_text
    assert "Phoenix,AZ       -> KPHX" in help_text
    assert "San Francisco,CA -> KSFO" in help_text
    assert "Seattle,WA       -> KSEA" in help_text
