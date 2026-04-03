from __future__ import annotations

import json

from weather_study_cli.application.sample_data import generate_sample_capture_directory
from weather_study_cli.application.raw_loader import load_capture_directory


class FakeObservedHighService:
    def fetch_observed_high_for_date(
        self,
        place: str,
        event_date: str,
        *,
        station_override: str | None = None,
        use_station_presets: bool = True,
    ) -> dict[str, object]:
        values = {
            ("Seattle,WA", "2026-03-26"): 52.0,
            ("Seattle,WA", "2026-03-27"): 57.9,
        }
        return {
            "observed_high_temperature_f": values[(place, event_date)],
        }


def test_generate_sample_capture_directory_builds_hourly_city_week(tmp_path):
    output_root = tmp_path / "raw"
    metadata_path = tmp_path / "sample-metadata.json"

    summary = generate_sample_capture_directory(
        output_root=output_root,
        metadata_path=metadata_path,
        places=("Seattle,WA",),
        day_count=2,
        end_local_date="2026-03-27",
        weather_service=FakeObservedHighService(),
    )

    assert summary.capture_count == 48
    assert summary.places == ("Seattle,WA",)
    assert summary.local_dates == ("2026-03-26", "2026-03-27")
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["actual_highs_f"]["Seattle,WA"]["2026-03-27"] == 57.9
    assert metadata["lock_in_hours"]["Seattle,WA"]["2026-03-26"] == 10

    dataset = load_capture_directory(output_root)
    assert dataset.file_count == 48
    assert dataset.cities == ("Seattle,WA",)
    assert dataset.capture_windows[0]["hours"] == list(range(24))
