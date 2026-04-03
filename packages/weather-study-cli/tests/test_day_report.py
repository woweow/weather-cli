from __future__ import annotations

from weather_study_cli.application import ingest_capture_directory, load_day_drilldown_report
from weather_study_cli.persistence import open_connection
from .support import LEGACY_RAW_DATA_DIR, insert_legacy_actuals


def test_load_day_drilldown_report_surfaces_partial_failures_and_actual_match(tmp_path):
    db_path = tmp_path / "study.db"
    ingest_capture_directory(LEGACY_RAW_DATA_DIR, db_path=db_path)

    with open_connection(db_path) as connection:
        insert_legacy_actuals(connection)
        connection.commit()

    summary = load_day_drilldown_report(
        db_path=db_path,
        place="Denver,CO",
        local_date="2026-03-27",
    )

    assert summary.capture_count == 2
    assert summary.correct_capture_count == 1
    assert summary.actual_high_temperature_f == 70.0

    morning = summary.captures[0]
    assert morning.local_hour == 8
    assert morning.weather_payload_present is False
    assert morning.market_payload_present is True
    assert morning.forecast_high_temperature_f is None
    assert morning.forecast_matches_actual is None
    assert morning.market_leader_label == "69\u00b0F to 70\u00b0F"
    assert morning.market_leader_last_price_cents == 37
    assert morning.error_sources == ("weather",)

    afternoon = summary.captures[1]
    assert afternoon.local_hour == 14
    assert afternoon.weather_payload_present is True
    assert afternoon.market_payload_present is True
    assert afternoon.forecast_high_temperature_f == 70.0
    assert afternoon.forecast_matches_actual is True
    assert afternoon.market_leader_label == "69\u00b0F to 70\u00b0F"
    assert afternoon.market_leader_last_price_cents == 59
