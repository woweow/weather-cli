from __future__ import annotations

import json
from pathlib import Path

from weather_study_cli.persistence.repository import upsert_daily_actual


TESTS_ROOT = Path(__file__).resolve().parent
LEGACY_RAW_DATA_DIR = TESTS_ROOT / "fixtures" / "legacy_raw"
SAMPLE_METADATA_PATH = TESTS_ROOT.parent / "mock-data" / "sample-week-metadata.json"

LEGACY_ACTUALS = {
    ("Seattle,WA", "2026-03-26"): 58.0,
    ("Seattle,WA", "2026-03-27"): 60.0,
    ("Denver,CO", "2026-03-26"): 72.0,
    ("Denver,CO", "2026-03-27"): 70.0,
}


def timezone_for_place(place: str) -> str:
    if place == "Seattle,WA":
        return "America/Los_Angeles"
    return "America/Denver"


def insert_legacy_actuals(connection, *, resolved_at_utc: str = "2026-03-29T22:00:00Z") -> None:
    for (place, local_date), high in LEGACY_ACTUALS.items():
        upsert_daily_actual(
            connection,
            place=place,
            local_date=local_date,
            timezone=timezone_for_place(place),
            observed_high_temperature_f=high,
            observed_payload={"source": "test", "observed_high_temperature_f": high},
            resolved_at_utc=resolved_at_utc,
        )


def load_sample_metadata() -> dict[str, object]:
    return json.loads(SAMPLE_METADATA_PATH.read_text(encoding="utf-8"))


def insert_sample_actuals(connection, *, resolved_at_utc: str = "2026-03-30T00:00:00Z") -> dict[str, object]:
    metadata = load_sample_metadata()
    actual_highs = metadata["actual_highs_f"]
    for place, by_date in actual_highs.items():
        for local_date, high in by_date.items():
            upsert_daily_actual(
                connection,
                place=place,
                local_date=local_date,
                timezone=timezone_for_place(place),
                observed_high_temperature_f=float(high),
                observed_payload={"source": "test", "observed_high_temperature_f": float(high)},
                resolved_at_utc=resolved_at_utc,
            )
    return metadata
