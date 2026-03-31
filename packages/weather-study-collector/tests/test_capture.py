from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime

from kalshi_weather_markets_cli.application.models import LadderSnapshot, MarketRange
from weather_study_cli.application import load_capture_directory
from weather_study_collector.application.capture import LiveStudyCollector


FIXED_CAPTURE_TIME = datetime(2026, 3, 29, 21, 0, tzinfo=UTC)


class FakeWeatherService:
    def fetch(self, place: str, range_name: str, *, now):
        assert range_name == "rest-of-today"
        assert now == FIXED_CAPTURE_TIME
        return {
            "location": {
                "input": place,
                "city": "Seattle",
                "state": "WA",
                "timezone": "America/Los_Angeles",
            },
            "resolved_coordinates": {
                "latitude": 47.6062,
                "longitude": -122.3321,
            },
            "range": {
                "name": "rest-of-today",
                "mode": "forecast",
                "start": "2026-03-29T14:00:00-07:00",
                "end": "2026-03-30T00:00:00-07:00",
            },
            "source": {
                "geocoder": "Open-Meteo geocoding",
                "provider": "NOAA weather.gov API",
                "point_url": "https://example.test/points/seattle",
                "station_selection": "forecast",
                "forecast_url": "https://example.test/forecast/seattle",
            },
            "station": None,
            "periods": [
                {
                    "kind": "forecast",
                    "start": "2026-03-29T14:00:00-07:00",
                    "end": "2026-03-29T15:00:00-07:00",
                    "temperature_f": 58.0,
                    "relative_humidity_pct": 52.0,
                    "precipitation_probability_pct": 10.0,
                    "wind_speed": "6 mph",
                    "wind_direction": "NW",
                    "summary": "Partly Sunny",
                }
            ],
        }


class FakeMarketService:
    def fetch_city_ladder(self, city: str, *, target_date: str | None = None) -> LadderSnapshot:
        assert city == "Seattle"
        assert target_date == "2026-03-29"
        return LadderSnapshot(
            provider="kalshi",
            city="Seattle",
            series_ticker="KXHIGHSEA",
            series_title="Seattle High Temperature",
            event_ticker="KXHIGHSEA-26MAR29",
            event_date="2026-03-29",
            event_date_label="Mar 29, 2026",
            markets=[
                MarketRange(
                    ticker="KXHIGHSEA-26MAR29-T58",
                    title="58F or below",
                    label="58F or below",
                    yes_bid_cents=48,
                    yes_ask_cents=52,
                    no_bid_cents=48,
                    no_ask_cents=52,
                    last_price_cents=50,
                    sort_key=58.0,
                )
            ],
        )


class FailingWeatherService:
    def fetch(self, place: str, range_name: str, *, now):
        raise RuntimeError(f"weather unavailable for {place}")


class RecordingMarketService:
    def __init__(self):
        self.calls = []

    def fetch_city_ladder(self, city: str, *, target_date: str | None = None) -> LadderSnapshot:
        self.calls.append((city, target_date))
        return LadderSnapshot(
            provider="kalshi",
            city="Seattle",
            series_ticker="KXHIGHSEA",
            series_title="Seattle High Temperature",
            event_ticker="KXHIGHSEA-26MAR30",
            event_date="2026-03-30",
            event_date_label="Mar 30, 2026",
            markets=[
                MarketRange(
                    ticker="KXHIGHSEA-26MAR30-T58",
                    title="58F or below",
                    label="58F or below",
                    yes_bid_cents=48,
                    yes_ask_cents=52,
                    no_bid_cents=48,
                    no_ask_cents=52,
                    last_price_cents=50,
                    sort_key=58.0,
                )
            ],
        )


class MidnightWeatherService:
    def fetch(self, place: str, range_name: str, *, now):
        assert place == "Seattle,WA"
        assert range_name == "rest-of-today"
        assert now == datetime(2026, 3, 30, 7, 0, tzinfo=UTC)
        return {
            "location": {
                "input": place,
                "city": "Seattle",
                "state": "WA",
                "timezone": "America/Los_Angeles",
            },
            "resolved_coordinates": {
                "latitude": 47.6062,
                "longitude": -122.3321,
            },
            "range": {
                "name": "rest-of-today",
                "mode": "forecast",
                "start": "2026-03-30T00:00:00-07:00",
                "end": "2026-03-31T00:00:00-07:00",
            },
            "source": {
                "geocoder": "Open-Meteo geocoding",
                "provider": "NOAA weather.gov API",
                "point_url": "https://example.test/points/seattle",
                "station_selection": "forecast",
                "forecast_url": "https://example.test/forecast/seattle",
            },
            "station": None,
            "periods": [
                {
                    "kind": "forecast",
                    "start": "2026-03-30T00:00:00-07:00",
                    "end": "2026-03-30T01:00:00-07:00",
                    "temperature_f": 49.0,
                    "relative_humidity_pct": 82.0,
                    "precipitation_probability_pct": 15.0,
                    "wind_speed": "4 mph",
                    "wind_direction": "S",
                    "summary": "Mostly Cloudy",
                }
            ],
        }


def test_capture_to_directory_writes_schema_valid_file(tmp_path):
    collector = LiveStudyCollector(FakeWeatherService(), FakeMarketService())

    summary = collector.capture_to_directory(
        output_root=tmp_path,
        places=["Seattle,WA"],
        captured_at_utc=FIXED_CAPTURE_TIME,
    )

    assert summary.success_count == 1
    assert summary.partial_count == 0
    dataset = load_capture_directory(tmp_path)
    assert dataset.file_count == 1
    assert dataset.cities == ("Seattle,WA",)


def test_capture_to_directory_persists_partial_failure_when_market_or_weather_is_missing(tmp_path):
    collector = LiveStudyCollector(FailingWeatherService(), FakeMarketService())

    summary = collector.capture_to_directory(
        output_root=tmp_path,
        places=["Seattle,WA"],
        captured_at_utc=FIXED_CAPTURE_TIME,
    )

    assert summary.success_count == 0
    assert summary.partial_count == 1
    dataset = load_capture_directory(tmp_path)
    assert dataset.file_count == 1
    capture_path = next(tmp_path.rglob("*.json"))
    payload = json.loads(capture_path.read_text(encoding="utf-8"))
    assert payload["weather"]["payload"] is None
    assert payload["market"]["payload"]["event_date"] == "2026-03-29"
    assert payload["errors"] == [
        {
            "source": "weather",
            "message": "RuntimeError: weather unavailable for Seattle,WA",
        }
    ]


def test_capture_to_directory_requests_market_ladder_for_local_capture_date(tmp_path):
    market_service = RecordingMarketService()
    collector = LiveStudyCollector(MidnightWeatherService(), market_service)

    summary = collector.capture_to_directory(
        output_root=tmp_path,
        places=["Seattle,WA"],
        captured_at_utc=datetime(2026, 3, 30, 7, 0, tzinfo=UTC),
    )

    assert summary.success_count == 1
    assert market_service.calls == [("Seattle", "2026-03-30")]
    payload = json.loads(next(tmp_path.rglob("*.json")).read_text(encoding="utf-8"))
    assert payload["capture_context"]["local_date"] == "2026-03-30"
    assert payload["market"]["payload"]["event_date"] == "2026-03-30"


def test_capture_to_s3_returns_uploaded_uri_summary(monkeypatch):
    collector = LiveStudyCollector(FakeWeatherService(), FakeMarketService())

    def fake_run(command, capture_output, text, check):
        assert command[:3] == ["aws", "s3", "sync"]
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("weather_study_collector.application.capture.subprocess.run", fake_run)

    summary = collector.capture_to_s3(
        bucket="weather-study-raw-084375548651-us-west-2",
        prefix="raw-live-smoke",
        profile="dev",
        places=["Seattle,WA"],
        captured_at_utc=FIXED_CAPTURE_TIME,
    )

    assert summary.uploaded_count == 1
    assert summary.results[0].s3_uri == (
        "s3://weather-study-raw-084375548651-us-west-2/"
        "raw-live-smoke/study_version=1/city=Seattle/state=WA/"
        "local_date=2026-03-29/local_hour=14/captured_at_utc=2026-03-29T21-00-00Z.json"
    )
