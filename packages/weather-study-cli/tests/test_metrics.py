from __future__ import annotations

import sqlite3

from weather_study_cli.application import compute_accuracy_metrics, ingest_capture_directory
from weather_study_cli.persistence import open_connection
from .support import LEGACY_RAW_DATA_DIR, insert_legacy_actuals


def test_compute_accuracy_metrics_uses_mock_aligned_actuals(tmp_path):
    db_path = tmp_path / "study.db"
    ingest_capture_directory(LEGACY_RAW_DATA_DIR, db_path=db_path)

    with open_connection(db_path) as connection:
        insert_legacy_actuals(connection, resolved_at_utc="2026-03-29T21:00:00Z")
        connection.commit()

    summary = compute_accuracy_metrics(db_path=db_path)

    assert summary.place_count == 2
    assert summary.metric_row_count == 4

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                place,
                local_hour,
                valid_day_count,
                missing_day_count,
                excluded_day_count,
                correct_day_count,
                ROUND(accuracy_ratio, 3)
            FROM hourly_accuracy_metrics
            ORDER BY place ASC, local_hour ASC
            """
        ).fetchall()

    assert rows == [
        ("Denver,CO", 8, 1, 0, 1, 1, 1.0),
        ("Denver,CO", 14, 2, 0, 0, 2, 1.0),
        ("Seattle,WA", 9, 2, 0, 0, 1, 0.5),
        ("Seattle,WA", 15, 2, 0, 0, 2, 1.0),
    ]
