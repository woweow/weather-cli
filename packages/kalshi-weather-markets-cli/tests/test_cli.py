import importlib

from kalshi_weather_markets_cli.cli import build_parser, main
from kalshi_weather_markets_cli.application.models import LadderSnapshot, MarketRange


def test_help_includes_examples_and_supported_cities():
    help_text = build_parser().format_help()

    assert "does not require API keys" in help_text
    assert "Use --list-cities for the live supported list." in help_text
    assert "earliest close time" in help_text
    assert "Normalized snapshot payload for scripting." in help_text
    assert "full active ladder" in help_text
    assert "`last_price_cents`" in help_text
    assert "weather-dashboard input" in help_text
    assert "Supported exact city names:" in help_text
    assert "Seattle" in help_text
    assert "Los Angeles" in help_text
    assert "kalshi-weather-markets Seattle" in help_text
    assert "kalshi-weather-markets --list-cities" in help_text
    assert 'kalshi-weather-markets "Los Angeles"' in help_text
    assert "seattle-market.json" in help_text


def test_list_cities_prints_supported_city_names(monkeypatch, capsys):
    class StubClient:
        pass

    class StubService:
        def __init__(self, client):
            assert isinstance(client, StubClient)

        def list_supported_cities(self):
            return ["Los Angeles", "Seattle"]

    cli_module = importlib.import_module("kalshi_weather_markets_cli.cli.main")
    monkeypatch.setattr(cli_module, "KalshiPublicClient", StubClient)
    monkeypatch.setattr(cli_module, "KalshiWeatherService", StubService)

    exit_code = main(["--list-cities"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "Los Angeles\nSeattle\n"


def test_json_output_uses_normalized_snapshot(monkeypatch, capsys):
    snapshot = LadderSnapshot(
        city="Seattle",
        series_ticker="KXHIGHTSEA",
        series_title="Seattle Maximum Temperature Daily",
        event_ticker="KXHIGHTSEA-26MAR26",
        event_date_label="Mar 26, 2026",
        markets=[
            MarketRange(
                ticker="KXHIGHTSEA-26MAR26-B53.5",
                title="Will the maximum temperature be  53-54° on Mar 26, 2026?",
                label="53° to 54°",
                yes_bid_cents=99,
                yes_ask_cents=100,
                no_bid_cents=0,
                no_ask_cents=1,
                last_price_cents=99,
                sort_key=53,
            )
        ],
    )

    class StubClient:
        pass

    class StubService:
        def __init__(self, client):
            assert isinstance(client, StubClient)

        def list_supported_cities(self):
            return ["Seattle"]

        def fetch_city_ladder(self, city):
            assert city == "Seattle"
            return snapshot

    cli_module = importlib.import_module("kalshi_weather_markets_cli.cli.main")
    monkeypatch.setattr(cli_module, "KalshiPublicClient", StubClient)
    monkeypatch.setattr(cli_module, "KalshiWeatherService", StubService)

    exit_code = main(["Seattle", "--format", "json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"city": "Seattle"' in captured.out
    assert '"label": "53\\u00b0 to 54\\u00b0"' in captured.out
