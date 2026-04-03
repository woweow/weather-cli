from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from weather_study_cli.application.cities import SUPPORTED_STUDY_CITIES
from weather_study_cli.application.gaps import load_collection_gap_report
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH


@dataclass(frozen=True)
class ValidStudyDayRow:
    place: str
    city: str
    valid_day_count: int
    has_captures: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "place": self.place,
            "city": self.city,
            "valid_day_count": self.valid_day_count,
            "has_captures": self.has_captures,
        }


@dataclass(frozen=True)
class ValidStudyDaysSummary:
    db_path: Path
    generated_at_utc: str
    places: tuple[ValidStudyDayRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_path": str(self.db_path),
            "generated_at_utc": self.generated_at_utc,
            "places": [p.to_dict() for p in self.places],
        }


def count_valid_study_days(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    now: datetime | None = None,
) -> ValidStudyDaysSummary:
    """Count complete local dates per study city using the same rules as `report-gaps`."""
    target_db_path = Path(db_path).expanduser().resolve()
    gap_report = load_collection_gap_report(db_path=target_db_path, place=None, now=now)
    by_place = {p.place: p for p in gap_report.places}
    rows: list[ValidStudyDayRow] = []
    for study_city in SUPPORTED_STUDY_CITIES:
        place = study_city.place
        gps = by_place.get(place)
        if gps is None:
            rows.append(
                ValidStudyDayRow(
                    place=place,
                    city=study_city.city,
                    valid_day_count=0,
                    has_captures=False,
                )
            )
        else:
            complete = sum(1 for d in gps.dates if d.missing_hour_count == 0)
            rows.append(
                ValidStudyDayRow(
                    place=place,
                    city=study_city.city,
                    valid_day_count=complete,
                    has_captures=True,
                )
            )
    return ValidStudyDaysSummary(
        db_path=target_db_path,
        generated_at_utc=gap_report.generated_at_utc,
        places=tuple(rows),
    )
