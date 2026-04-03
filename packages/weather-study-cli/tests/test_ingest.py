from __future__ import annotations

import sqlite3

from weather_study_cli.application import ingest_capture_directory
from .support import LEGACY_RAW_DATA_DIR


def test_ingest_capture_directory_is_idempotent(tmp_path):
    db_path = tmp_path / "study.db"

    first = ingest_capture_directory(LEGACY_RAW_DATA_DIR, db_path=db_path)
    second = ingest_capture_directory(LEGACY_RAW_DATA_DIR, db_path=db_path)

    assert first.ingested_capture_count == 8
    assert second.raw_capture_count == 8
    assert second.forecast_period_count == 21
    assert second.market_row_count == 22
    assert second.daily_actual_count == 0
    assert second.hourly_accuracy_metric_count == 0
    assert second.hourly_market_opportunity_metric_count == 0

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM raw_captures").fetchone()[0] == 8
        assert connection.execute("SELECT COUNT(*) FROM forecast_periods").fetchone()[0] == 21
        assert connection.execute("SELECT COUNT(*) FROM market_rows").fetchone()[0] == 22
        assert connection.execute("SELECT COUNT(*) FROM daily_actuals").fetchone()[0] == 0
