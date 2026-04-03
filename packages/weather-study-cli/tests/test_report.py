from __future__ import annotations

from weather_study_cli.application import (
    compute_accuracy_metrics,
    compute_market_opportunity_metrics,
    ingest_capture_directory,
)
from weather_study_cli.application.report import load_accuracy_dashboard_report
from weather_study_cli.persistence import open_connection
from .support import LEGACY_RAW_DATA_DIR, insert_legacy_actuals


def test_load_accuracy_dashboard_report_includes_hourly_market_annotations(tmp_path):
    db_path = tmp_path / "study.db"
    ingest_capture_directory(LEGACY_RAW_DATA_DIR, db_path=db_path)

    with open_connection(db_path) as connection:
        insert_legacy_actuals(connection)
        connection.commit()

    compute_accuracy_metrics(db_path=db_path)
    compute_market_opportunity_metrics(db_path=db_path)

    report = load_accuracy_dashboard_report(db_path=db_path, min_valid_sample=5).to_dict()
    cities = {city["place"]: city for city in report["cities"]}

    assert cities["Denver,CO"]["capture_day_count"] == 2
    assert cities["Denver,CO"]["resolved_actual_day_count"] == 2
    assert cities["Denver,CO"]["capture_window_start_date"] == "2026-03-26"
    assert cities["Denver,CO"]["capture_window_end_date"] == "2026-03-27"

    denver_first = cities["Denver,CO"]["points"][0]
    assert denver_first["local_hour"] == 8
    assert denver_first["accuracy_ratio"] == 1.0
    assert denver_first["thin_sample"] is True
    assert denver_first["winning_market_label"] == "69°F to 70°F"
    assert denver_first["avg_winning_bucket_last_price_cents"] == 38.5
    assert denver_first["winning_market_sample_count"] == 2

    seattle_last = cities["Seattle,WA"]["points"][-1]
    assert seattle_last["local_hour"] == 15
    assert seattle_last["accuracy_ratio"] == 1.0
    assert seattle_last["thin_sample"] is True
    assert seattle_last["winning_market_label"] == "57°F to 58°F"
