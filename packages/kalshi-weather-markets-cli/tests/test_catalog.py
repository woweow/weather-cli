from kalshi_weather_markets_cli.application.catalog import (
    build_city_catalog,
    documented_cities_help_text,
)


def test_build_city_catalog_filters_and_sorts_candidates():
    catalog = build_city_catalog(
        [
            {
                "ticker": "KXHIGHTSEA",
                "title": "Seattle Maximum Temperature Daily",
                "category": "Climate and Weather",
                "frequency": "daily",
                "tags": ["Daily temperature"],
                "last_updated_ts": "2026-03-12T18:01:57Z",
            },
            {
                "ticker": "KXHOUHIGH",
                "title": "Highest temperature in Houston",
                "category": "Climate and Weather",
                "frequency": "daily",
                "tags": ["Daily temperature"],
                "last_updated_ts": "2026-03-16T15:06:27Z",
            },
            {
                "ticker": "KXHIGHHOU",
                "title": "Highest temperature in Houston",
                "category": "Climate and Weather",
                "frequency": "daily",
                "tags": ["Daily temperature"],
                "last_updated_ts": "2026-03-16T15:06:28Z",
            },
            {
                "ticker": "KXLOWTSEA",
                "title": "Lowest temperature in Seattle",
                "category": "Climate and Weather",
                "frequency": "daily",
                "tags": ["Daily temperature"],
                "last_updated_ts": "2026-03-12T18:01:57Z",
            },
        ]
    )

    assert sorted(catalog) == ["Houston", "Seattle"]
    assert [candidate.series_ticker for candidate in catalog["Houston"]] == [
        "KXHIGHHOU",
        "KXHOUHIGH",
    ]
    assert catalog["Seattle"][0].series_ticker == "KXHIGHTSEA"


def test_documented_cities_help_text_lists_seattle():
    assert "Seattle" in documented_cities_help_text()
    assert "Los Angeles" in documented_cities_help_text()
