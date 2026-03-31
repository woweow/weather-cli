import pytest

from kalshi_weather_markets_cli.application.errors import UnsupportedCityError
from kalshi_weather_markets_cli.application.service import KalshiWeatherService, format_event_date


class FakeKalshiClient:
    def list_series(self):
        return [
            {
                "ticker": "KXHIGHTSEA",
                "title": "Seattle Maximum Temperature Daily",
                "category": "Climate and Weather",
                "frequency": "daily",
                "tags": ["Daily temperature"],
                "last_updated_ts": "2026-03-12T18:01:57Z",
            },
            {
                "ticker": "KXHIGHHOU",
                "title": "Highest temperature in Houston",
                "category": "Climate and Weather",
                "frequency": "daily",
                "tags": ["Daily temperature"],
                "last_updated_ts": "2026-03-16T15:06:28Z",
            },
        ]

    def get_markets(self, series_ticker, *, status="open", limit=1000):
        assert status == "open"
        assert limit == 1000
        if series_ticker != "KXHIGHTSEA":
            return []
        return [
            {
                "ticker": "KXHIGHTSEA-26MAR27-T60",
                "event_ticker": "KXHIGHTSEA-26MAR27",
                "title": "Will the maximum temperature be  >60° on Mar 27, 2026?",
                "close_time": "2026-03-28T08:00:00Z",
                "strike_type": "greater",
                "floor_strike": 60,
                "yes_sub_title": "61° or above",
                "yes_bid_dollars": "0.02",
                "yes_ask_dollars": "0.03",
                "no_bid_dollars": "0.97",
                "no_ask_dollars": "0.98",
                "last_price_dollars": "0.03",
            },
            {
                "ticker": "KXHIGHTSEA-26MAR26-B49.5",
                "event_ticker": "KXHIGHTSEA-26MAR26",
                "title": "Will the maximum temperature be  49-50° on Mar 26, 2026?",
                "close_time": "2026-03-27T08:00:00Z",
                "strike_type": "between",
                "floor_strike": 49,
                "cap_strike": 50,
                "yes_sub_title": "49° to 50°",
                "yes_bid_dollars": "0.00",
                "yes_ask_dollars": "0.01",
                "no_bid_dollars": "0.99",
                "no_ask_dollars": "1.00",
                "last_price_dollars": "0.01",
            },
            {
                "ticker": "KXHIGHTSEA-26MAR26-T49",
                "event_ticker": "KXHIGHTSEA-26MAR26",
                "title": "Will the maximum temperature be  <49° on Mar 26, 2026?",
                "close_time": "2026-03-27T08:00:00Z",
                "strike_type": "less",
                "cap_strike": 49,
                "yes_sub_title": "48° or below",
                "yes_bid_dollars": "0.00",
                "yes_ask_dollars": "0.01",
                "no_bid_dollars": "0.99",
                "no_ask_dollars": "1.00",
                "last_price_dollars": "0.01",
            },
            {
                "ticker": "KXHIGHTSEA-26MAR26-B53.5",
                "event_ticker": "KXHIGHTSEA-26MAR26",
                "title": "Will the maximum temperature be  53-54° on Mar 26, 2026?",
                "close_time": "2026-03-27T08:00:00Z",
                "strike_type": "between",
                "floor_strike": 53,
                "cap_strike": 54,
                "yes_sub_title": "53° to 54°",
                "yes_bid_dollars": "0.99",
                "yes_ask_dollars": "1.00",
                "no_bid_dollars": "0.00",
                "no_ask_dollars": "0.01",
                "last_price_dollars": "0.99",
            },
            {
                "ticker": "KXHIGHTSEA-26MAR26-T56",
                "event_ticker": "KXHIGHTSEA-26MAR26",
                "title": "Will the maximum temperature be  >56° on Mar 26, 2026?",
                "close_time": "2026-03-27T08:00:00Z",
                "strike_type": "greater",
                "floor_strike": 56,
                "yes_sub_title": "57° or above",
                "yes_bid_dollars": "0.00",
                "yes_ask_dollars": "0.01",
                "no_bid_dollars": "0.99",
                "no_ask_dollars": "1.00",
                "last_price_dollars": "0.01",
            },
        ]


def test_fetch_city_ladder_selects_current_event_and_sorts_ranges():
    service = KalshiWeatherService(client=FakeKalshiClient())

    snapshot = service.fetch_city_ladder("Seattle")

    assert snapshot.series_ticker == "KXHIGHTSEA"
    assert snapshot.event_ticker == "KXHIGHTSEA-26MAR26"
    assert snapshot.event_date_label == "Mar 26, 2026"
    assert [market.label for market in snapshot.markets] == [
        "48° or below",
        "49° to 50°",
        "53° to 54°",
        "57° or above",
    ]
    assert snapshot.markets[2].yes_bid_cents == 99


def test_fetch_city_ladder_prefers_requested_target_date_when_multiple_events_are_open():
    service = KalshiWeatherService(client=FakeKalshiClient())

    snapshot = service.fetch_city_ladder("Seattle", target_date="2026-03-27")

    assert snapshot.event_ticker == "KXHIGHTSEA-26MAR27"
    assert snapshot.event_date == "2026-03-27"
    assert [market.label for market in snapshot.markets] == ["61° or above"]


def test_fetch_city_ladder_rejects_unknown_city():
    service = KalshiWeatherService(client=FakeKalshiClient())

    with pytest.raises(UnsupportedCityError):
        service.fetch_city_ladder("Portland")


def test_format_event_date_uses_year_month_day_ticker_order():
    assert format_event_date("KXHIGHTSEA-26MAR27") == "Mar 27, 2026"
