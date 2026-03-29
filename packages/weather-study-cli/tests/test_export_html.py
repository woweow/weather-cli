from __future__ import annotations

from weather_study_cli.application import (
    DEFAULT_MOCK_DATA_DIR,
    compute_accuracy_metrics,
    compute_market_opportunity_metrics,
    export_accuracy_html,
    ingest_capture_directory,
)
from weather_study_cli.persistence import open_connection
from weather_study_cli.persistence.repository import upsert_daily_actual


def test_export_accuracy_html_writes_self_contained_dashboard(tmp_path):
    db_path = tmp_path / "study.db"
    output_path = tmp_path / "accuracy.html"
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
                resolved_at_utc="2026-03-29T21:00:00Z",
            )
        connection.commit()

    compute_accuracy_metrics(db_path=db_path)
    compute_market_opportunity_metrics(db_path=db_path)
    export_accuracy_html(db_path=db_path, output_path=output_path, min_valid_sample=5)

    html = output_path.read_text(encoding="utf-8")
    assert "Forecast Confidence Atlas" in html
    assert "Market Convergence" in html
    assert "Single-Day Drilldown" in html
    assert "Example Days" in html
    assert "Avg winner" in html
    assert "Seattle,WA" in html
    assert "Denver,CO" in html
    assert "Thin sample" in html


def test_export_accuracy_html_marks_zero_valid_hours_as_unresolved(tmp_path):
    db_path = tmp_path / "study.db"
    output_path = tmp_path / "accuracy-unresolved.html"
    ingest_capture_directory(DEFAULT_MOCK_DATA_DIR, db_path=db_path)

    compute_accuracy_metrics(db_path=db_path)
    compute_market_opportunity_metrics(db_path=db_path)
    export_accuracy_html(db_path=db_path, output_path=output_path, min_valid_sample=5)

    html = output_path.read_text(encoding="utf-8")
    assert "No finalized accuracy days yet" in html
    assert "No finalized market days yet" in html
    assert "Unresolved" in html
