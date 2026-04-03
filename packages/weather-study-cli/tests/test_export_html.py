from __future__ import annotations

import json
import re

from weather_study_cli.application import (
    DEFAULT_MOCK_DATA_DIR,
    compute_accuracy_metrics,
    compute_market_opportunity_metrics,
    export_accuracy_html,
    ingest_capture_directory,
)
from weather_study_cli.persistence import open_connection
from .support import insert_sample_actuals


def test_export_accuracy_html_writes_self_contained_dashboard(tmp_path):
    db_path = tmp_path / "study.db"
    output_path = tmp_path / "accuracy.html"
    ingest_capture_directory(DEFAULT_MOCK_DATA_DIR, db_path=db_path)

    with open_connection(db_path) as connection:
        metadata = insert_sample_actuals(connection, resolved_at_utc="2026-03-30T00:00:00Z")
        connection.commit()

    compute_accuracy_metrics(db_path=db_path)
    compute_market_opportunity_metrics(db_path=db_path)
    export_accuracy_html(db_path=db_path, output_path=output_path, min_valid_sample=5)

    html = output_path.read_text(encoding="utf-8")
    report_blob = re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    assert report_blob is not None
    embedded_report = json.loads(report_blob.group(1))

    assert "Daily High Accuracy Study" in html
    assert "When Each City Finally Gets It Right" in html
    assert "Resolved Days" in html
    assert "Seattle,WA" in html
    assert "Denver,CO" in html
    assert "City Selector" not in html
    assert "Trust Thresholds" not in html
    assert "Collection Gaps" not in html
    cities = {city["place"]: city for city in embedded_report["cities"]}
    assert cities["Denver,CO"]["capture_day_count"] == 7
    assert cities["Denver,CO"]["resolved_actual_day_count"] == 7
    assert cities["Denver,CO"]["capture_window_start_date"] == "2026-03-22"
    assert cities["Denver,CO"]["capture_window_end_date"] == "2026-03-28"
    assert len(cities["Seattle,WA"]["points"]) == 24
    seattle_ten_am = cities["Seattle,WA"]["points"][10]
    assert seattle_ten_am["correct_day_count"] == 1
    assert seattle_ten_am["valid_day_count"] == 7
    assert round(seattle_ten_am["accuracy_ratio"], 3) == 0.143
    assert seattle_ten_am["winning_market_label"] == "49F to 50F"
    assert metadata["local_dates"][0] == "2026-03-22"


def test_export_accuracy_html_renders_na_market_annotations_without_actuals(tmp_path):
    db_path = tmp_path / "study.db"
    output_path = tmp_path / "accuracy-unresolved.html"
    ingest_capture_directory(DEFAULT_MOCK_DATA_DIR, db_path=db_path)

    compute_accuracy_metrics(db_path=db_path)
    compute_market_opportunity_metrics(db_path=db_path)
    export_accuracy_html(db_path=db_path, output_path=output_path, min_valid_sample=5)

    html = output_path.read_text(encoding="utf-8")
    report_blob = re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    assert report_blob is not None
    embedded_report = json.loads(report_blob.group(1))
    first_city = embedded_report["cities"][0]
    assert all(point["correct_day_count"] == 0 for point in first_city["points"])
    assert all(point["winning_market_label"] is None for point in first_city["points"])
    assert "n/a" in html
