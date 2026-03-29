from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from weather_study_cli.application import DEFAULT_MOCK_DATA_DIR, derive_daily_actuals, ingest_capture_directory


class FakeObservedHighService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.highs = {
            ("Denver,CO", "2026-03-26"): 72.0,
            ("Denver,CO", "2026-03-27"): 70.0,
            ("Seattle,WA", "2026-03-26"): 58.0,
            ("Seattle,WA", "2026-03-27"): 60.0,
        }

    def fetch_observed_high_for_date(
        self,
        place: str,
        event_date: str,
        *,
        station_override: str | None = None,
        use_station_presets: bool = True,
    ) -> dict[str, object]:
        self.calls.append((place, event_date))
        return {
            "location": {
                "input": place,
                "city": place.split(",")[0],
                "state": place.split(",")[1],
                "timezone": "America/Los_Angeles" if place == "Seattle,WA" else "America/Denver",
            },
            "event_date": event_date,
            "observed_high_temperature_f": self.highs[(place, event_date)],
            "station": {
                "identifier": "TEST",
                "name": "Test Station",
                "timezone": "America/Los_Angeles" if place == "Seattle,WA" else "America/Denver",
            },
            "station_selection": "preset" if use_station_presets else "nearest",
        }


def test_derive_daily_actuals_skips_incomplete_days_and_upserts_results(tmp_path):
    db_path = tmp_path / "study.db"
    ingest_capture_directory(DEFAULT_MOCK_DATA_DIR, db_path=db_path)
    service = FakeObservedHighService()

    first = derive_daily_actuals(
        db_path=db_path,
        now=datetime(2026, 3, 27, 20, 0, tzinfo=UTC),
        weather_service=service,
    )
    second = derive_daily_actuals(
        db_path=db_path,
        now=datetime(2026, 3, 29, 20, 0, tzinfo=UTC),
        weather_service=service,
    )

    assert first.target_count == 4
    assert first.resolved_count == 2
    assert first.skipped_incomplete_count == 2
    assert first.daily_actual_count == 2
    assert second.resolved_count == 4
    assert second.skipped_incomplete_count == 0
    assert second.daily_actual_count == 4

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT place, local_date, observed_high_temperature_f
            FROM daily_actuals
            ORDER BY place ASC, local_date ASC
            """
        ).fetchall()

    assert rows == [
        ("Denver,CO", "2026-03-26", 72.0),
        ("Denver,CO", "2026-03-27", 70.0),
        ("Seattle,WA", "2026-03-26", 58.0),
        ("Seattle,WA", "2026-03-27", 60.0),
    ]
