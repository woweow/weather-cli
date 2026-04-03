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


def _tz_suffix(tz: str) -> str:
    if tz == "America/Los_Angeles":
        return "-07:00"
    return "-06:00"


def _legacy_observation_periods(place: str, local_date: str, high: float) -> list[dict[str, object]]:
    tz = timezone_for_place(place)
    hi = int(round(high))
    suf = _tz_suffix(tz)
    return [
        {
            "kind": "observation",
            "start": f"{local_date}T06:00:00{suf}",
            "end": f"{local_date}T06:00:00{suf}",
            "temperature_f": float(hi - 20),
        },
        {
            "kind": "observation",
            "start": f"{local_date}T12:00:00{suf}",
            "end": f"{local_date}T12:00:00{suf}",
            "temperature_f": float(hi - 5),
        },
        {
            "kind": "observation",
            "start": f"{local_date}T17:00:00{suf}",
            "end": f"{local_date}T17:00:00{suf}",
            "temperature_f": float(hi),
        },
    ]


def insert_legacy_actuals(connection, *, resolved_at_utc: str = "2026-03-29T22:00:00Z") -> None:
    for (place, local_date), high in LEGACY_ACTUALS.items():
        periods = _legacy_observation_periods(place, local_date, high)
        upsert_daily_actual(
            connection,
            place=place,
            local_date=local_date,
            timezone=timezone_for_place(place),
            observed_high_temperature_f=high,
            observed_payload={
                "source": "test",
                "observed_high_temperature_f": high,
                "periods": periods,
            },
            resolved_at_utc=resolved_at_utc,
        )


def load_sample_metadata() -> dict[str, object]:
    return json.loads(SAMPLE_METADATA_PATH.read_text(encoding="utf-8"))


def _sample_observation_periods(place: str, local_date: str, high: float, lock_in_hour: int) -> list[dict[str, object]]:
    tz = timezone_for_place(place)
    suf = _tz_suffix(tz)
    hi = int(round(float(high)))
    lh = max(0, min(23, int(lock_in_hour)))
    return [
        {
            "kind": "observation",
            "start": f"{local_date}T06:00:00{suf}",
            "end": f"{local_date}T06:00:00{suf}",
            "temperature_f": float(hi - 30),
        },
        {
            "kind": "observation",
            "start": f"{local_date}T{lh:02d}:00:00{suf}",
            "end": f"{local_date}T{lh:02d}:00:00{suf}",
            "temperature_f": float(hi),
        },
    ]


def insert_sample_actuals(connection, *, resolved_at_utc: str = "2026-03-30T00:00:00Z") -> dict[str, object]:
    metadata = load_sample_metadata()
    actual_highs = metadata["actual_highs_f"]
    lock_hours = metadata.get("lock_in_hours") or {}
    for place, by_date in actual_highs.items():
        place_locks = lock_hours.get(place) or {}
        for local_date, high in by_date.items():
            lock_h = int(place_locks.get(local_date, 12))
            periods = _sample_observation_periods(place, local_date, float(high), lock_h)
            upsert_daily_actual(
                connection,
                place=place,
                local_date=local_date,
                timezone=timezone_for_place(place),
                observed_high_temperature_f=float(high),
                observed_payload={
                    "source": "test",
                    "observed_high_temperature_f": float(high),
                    "periods": periods,
                },
                resolved_at_utc=resolved_at_utc,
            )
    return metadata
