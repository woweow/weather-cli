from __future__ import annotations

from weather_study_cli.application import build_study_report
from weather_study_cli.cli.main import render_build_report_text_summary
from .support import LEGACY_RAW_DATA_DIR


class FakeObservedHighService:
    def __init__(self, values: dict[tuple[str, str], float]) -> None:
        self._values = values

    def fetch_observed_high_for_date(
        self,
        place: str,
        event_date: str,
        *,
        station_override: str | None = None,
        use_station_presets: bool = True,
    ) -> dict[str, float]:
        return {
            "observed_high_temperature_f": self._values[(place, event_date)],
        }


def test_build_study_report_includes_city_maturity_summary(tmp_path):
    db_path = tmp_path / "study.db"
    output_path = tmp_path / "study.html"
    summary = build_study_report(
        input_path=LEGACY_RAW_DATA_DIR,
        db_path=db_path,
        output_path=output_path,
        weather_service=FakeObservedHighService(
            {
                ("Seattle,WA", "2026-03-26"): 52.0,
                ("Seattle,WA", "2026-03-27"): 57.9,
                ("Denver,CO", "2026-03-26"): 71.6,
                ("Denver,CO", "2026-03-27"): 55.4,
            }
        ),
    )

    assert output_path.exists()
    assert [city.place for city in summary.cities] == ["Denver,CO", "Seattle,WA"]
    assert summary.to_dict()["cities"] == [
        {
            "place": "Denver,CO",
            "timezone": "America/Denver",
            "study_day_count": 2,
            "capture_day_count": 2,
            "resolved_actual_day_count": 2,
            "capture_window_start_date": "2026-03-26",
            "capture_window_end_date": "2026-03-27",
        },
        {
            "place": "Seattle,WA",
            "timezone": "America/Los_Angeles",
            "study_day_count": 2,
            "capture_day_count": 2,
            "resolved_actual_day_count": 2,
            "capture_window_start_date": "2026-03-26",
            "capture_window_end_date": "2026-03-27",
        },
    ]

    text = render_build_report_text_summary(summary)
    assert "city maturity:" in text
    assert "Denver,CO: 2/2 resolved days, window 2026-03-26 -> 2026-03-27" in text
    assert "Seattle,WA: 2/2 resolved days, window 2026-03-26 -> 2026-03-27" in text
