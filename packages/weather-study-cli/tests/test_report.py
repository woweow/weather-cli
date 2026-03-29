from __future__ import annotations

from weather_study_cli.application import (
    DEFAULT_MOCK_DATA_DIR,
    compute_accuracy_metrics,
    compute_market_opportunity_metrics,
    ingest_capture_directory,
)
from weather_study_cli.application.report import load_accuracy_dashboard_report
from weather_study_cli.persistence import open_connection
from weather_study_cli.persistence.repository import upsert_daily_actual


def test_load_accuracy_dashboard_report_includes_threshold_summary(tmp_path):
    db_path = tmp_path / "study.db"
    ingest_capture_directory(DEFAULT_MOCK_DATA_DIR, db_path=db_path)

    with open_connection(db_path) as connection:
        for place, local_date, timezone, high in (
            ("Seattle,WA", "2026-03-26", "America/Los_Angeles", 58.0),
            ("Seattle,WA", "2026-03-27", "America/Los_Angeles", 60.0),
            ("Denver,CO", "2026-03-26", "America/Denver", 72.0),
            ("Denver,CO", "2026-03-27", "America/Denver", 70.0),
        ):
            upsert_daily_actual(
                connection,
                place=place,
                local_date=local_date,
                timezone=timezone,
                observed_high_temperature_f=high,
                observed_payload={"source": "test", "observed_high_temperature_f": high},
                resolved_at_utc="2026-03-29T22:00:00Z",
            )
        connection.commit()

    compute_accuracy_metrics(db_path=db_path)
    compute_market_opportunity_metrics(db_path=db_path)

    report = load_accuracy_dashboard_report(db_path=db_path, min_valid_sample=5).to_dict()
    cities = {city["place"]: city for city in report["cities"]}

    denver_sixty = cities["Denver,CO"]["threshold_summary"][0]
    assert denver_sixty == {
        "threshold_ratio": 0.6,
        "threshold_label": "60%",
        "status": "reached",
        "local_hour": 8,
        "accuracy_ratio": 1.0,
        "valid_day_count": 1,
        "correct_day_count": 1,
        "thin_sample": True,
        "market_summary": {
            "valid_day_count": 2,
            "leader_match_day_count": 2,
            "leader_match_ratio": 1.0,
            "avg_winning_bucket_last_price_cents": 38.5,
        },
    }

    seattle_sixty = cities["Seattle,WA"]["threshold_summary"][0]
    assert seattle_sixty["status"] == "reached"
    assert seattle_sixty["local_hour"] == 15
    assert seattle_sixty["accuracy_ratio"] == 1.0
    assert seattle_sixty["thin_sample"] is True
    assert seattle_sixty["market_summary"]["leader_match_ratio"] == 1.0
