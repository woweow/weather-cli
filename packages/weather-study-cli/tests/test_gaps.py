from __future__ import annotations

from datetime import UTC, datetime

from weather_study_cli.application import (
    DEFAULT_MOCK_DATA_DIR,
    ingest_capture_directory,
    load_collection_gap_report,
)


def test_load_collection_gap_report_counts_missing_mock_hours(tmp_path):
    db_path = tmp_path / "study.db"
    ingest_capture_directory(DEFAULT_MOCK_DATA_DIR, db_path=db_path)

    summary = load_collection_gap_report(
        db_path=db_path,
        now=datetime(2026, 3, 29, 22, 0, tzinfo=UTC),
    )

    assert summary.place_count == 2
    assert summary.date_count == 4
    assert summary.expected_hour_count == 79
    assert summary.observed_hour_count == 8
    assert summary.missing_hour_count == 71
    assert summary.gap_date_count == 4

    places = {place.place: place for place in summary.places}

    seattle = places["Seattle,WA"]
    assert seattle.expected_hour_count == 39
    assert seattle.observed_hour_count == 4
    assert seattle.missing_hour_count == 35

    first_day = seattle.dates[0]
    assert first_day.local_date == "2026-03-26"
    assert first_day.expected_start_hour == 9
    assert first_day.expected_end_hour == 23
    assert first_day.observed_hours == (9, 15)
    assert first_day.missing_hours[:3] == (10, 11, 12)
    assert first_day.missing_hours[-2:] == (22, 23)

    second_day = seattle.dates[1]
    assert second_day.local_date == "2026-03-27"
    assert second_day.expected_start_hour == 0
    assert second_day.expected_end_hour == 23
    assert second_day.missing_hours[:3] == (0, 1, 2)
    assert second_day.missing_hours[-2:] == (22, 23)
