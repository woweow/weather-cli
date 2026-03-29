from __future__ import annotations

import json

import pytest

from weather_study_cli.application import DEFAULT_MOCK_DATA_DIR, StudyValidationError, load_capture_directory


def test_load_capture_directory_validates_bundled_mock_data():
    summary = load_capture_directory(DEFAULT_MOCK_DATA_DIR)

    assert summary.file_count == 8
    assert summary.cities == ("Denver,CO", "Seattle,WA")
    assert summary.local_dates == ("2026-03-26", "2026-03-27")
    assert summary.weather_missing_count == 1
    assert summary.market_missing_count == 1
    assert summary.capture_windows[0]["hours"] == [8, 14]


def test_load_capture_directory_accepts_single_capture_file():
    file_path = (
        DEFAULT_MOCK_DATA_DIR
        / "study_version=1"
        / "city=Seattle"
        / "state=WA"
        / "local_date=2026-03-26"
        / "local_hour=09"
        / "captured_at_utc=2026-03-26T16-00-00Z.json"
    )

    summary = load_capture_directory(file_path)

    assert summary.file_count == 1
    assert summary.cities == ("Seattle,WA",)
    assert summary.local_dates == ("2026-03-26",)


def test_load_capture_directory_rejects_path_payload_mismatch(tmp_path):
    file_path = (
        tmp_path
        / "study_version=1"
        / "city=Seattle"
        / "state=WA"
        / "local_date=2026-03-26"
        / "local_hour=09"
        / "captured_at_utc=2026-03-26T16-00-00Z.json"
    )
    file_path.parent.mkdir(parents=True)
    payload = {
        "schema_version": "1",
        "captured_at_utc": "2026-03-26T16:00:00Z",
        "collector": {"name": "weather-market-study-mock", "version": "1"},
        "city": {
            "name": "Denver",
            "state": "CO",
            "place": "Denver,CO",
            "timezone": "America/Denver",
        },
        "capture_context": {
            "local_timestamp": "2026-03-26T09:00:00-07:00",
            "local_date": "2026-03-26",
            "local_hour": 9,
        },
        "weather": {"source": "weather-cli rest-of-today", "payload": None},
        "market": {
            "source": "kalshi-weather-markets --format json",
            "payload": {
                "provider": "kalshi",
                "city": "Denver",
                "series_ticker": "KXHIGHTDEN",
                "series_title": "Denver Maximum Temperature Daily",
                "event_ticker": "KXHIGHTDEN-26MAR26",
                "event_date": "2026-03-26",
                "event_date_label": "Mar 26, 2026",
                "markets": [{"ticker": "KXHIGHTDEN-26MAR26-B69.5", "label": "69°F to 70°F"}],
            },
        },
        "errors": [{"source": "weather", "message": "missing weather payload"}],
    }
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(StudyValidationError, match="city.name must match the city path segment"):
        load_capture_directory(tmp_path)
