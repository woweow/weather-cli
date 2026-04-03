from __future__ import annotations

from datetime import UTC, datetime

from weather_study_cli.application import (
    count_valid_study_days,
    ingest_capture_directory,
)
from .support import LEGACY_RAW_DATA_DIR


def test_count_valid_study_days_lists_all_cities_and_counts_complete_days(tmp_path):
    db_path = tmp_path / "study.db"
    ingest_capture_directory(LEGACY_RAW_DATA_DIR, db_path=db_path)

    summary = count_valid_study_days(
        db_path=db_path,
        now=datetime(2026, 3, 29, 22, 0, tzinfo=UTC),
    )

    assert summary.db_path == db_path.resolve()
    by_city = {row.city: row for row in summary.places}
    assert len(by_city) == 6
    assert by_city["Seattle"].valid_day_count == 0
    assert by_city["Seattle"].has_captures is True
    assert by_city["Denver"].valid_day_count == 0
    assert by_city["San Francisco"].valid_day_count == 0
    assert by_city["San Francisco"].has_captures is False
