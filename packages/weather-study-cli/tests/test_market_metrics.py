from __future__ import annotations

import sqlite3

from weather_study_cli.application import (
    compute_market_opportunity_metrics,
    ingest_capture_directory,
)
from weather_study_cli.persistence import open_connection
from .support import LEGACY_RAW_DATA_DIR, insert_legacy_actuals


def test_compute_market_opportunity_metrics_joins_actuals_to_winning_buckets(tmp_path):
    db_path = tmp_path / "study.db"
    ingest_capture_directory(LEGACY_RAW_DATA_DIR, db_path=db_path)

    with open_connection(db_path) as connection:
        insert_legacy_actuals(connection)
        connection.commit()

    summary = compute_market_opportunity_metrics(db_path=db_path)

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
                leader_match_day_count,
                ROUND(leader_match_ratio, 3),
                ROUND(avg_winning_bucket_last_price_cents, 1)
            FROM hourly_market_opportunity_metrics
            ORDER BY place ASC, local_hour ASC
            """
        ).fetchall()

    assert rows == [
        ("Denver,CO", 8, 2, 0, 0, 2, 1.0, 38.5),
        ("Denver,CO", 14, 1, 0, 1, 1, 1.0, 59.0),
        ("Seattle,WA", 9, 1, 0, 1, 1, 1.0, 42.0),
        ("Seattle,WA", 15, 2, 0, 0, 2, 1.0, 64.0),
    ]
