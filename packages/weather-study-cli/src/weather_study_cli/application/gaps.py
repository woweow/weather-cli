from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from weather_study_cli.application.cities import list_supported_study_places
from weather_study_cli.application.errors import StudyValidationError
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import list_capture_hour_rows


@dataclass(frozen=True)
class GapDateSummary:
    local_date: str
    expected_start_hour: int
    expected_end_hour: int
    expected_hour_count: int
    observed_hour_count: int
    missing_hour_count: int
    observed_hours: tuple[int, ...]
    missing_hours: tuple[int, ...]
    is_current_local_date: bool

    @property
    def coverage_ratio(self) -> float:
        if self.expected_hour_count == 0:
            return 1.0
        return self.observed_hour_count / self.expected_hour_count

    def to_dict(self) -> dict[str, object]:
        return {
            "local_date": self.local_date,
            "expected_start_hour": self.expected_start_hour,
            "expected_end_hour": self.expected_end_hour,
            "expected_hour_count": self.expected_hour_count,
            "observed_hour_count": self.observed_hour_count,
            "missing_hour_count": self.missing_hour_count,
            "coverage_ratio": self.coverage_ratio,
            "observed_hours": list(self.observed_hours),
            "missing_hours": list(self.missing_hours),
            "is_current_local_date": self.is_current_local_date,
        }


@dataclass(frozen=True)
class GapPlaceSummary:
    place: str
    timezone: str
    expected_hour_count: int
    observed_hour_count: int
    missing_hour_count: int
    gap_date_count: int
    dates: tuple[GapDateSummary, ...]

    @property
    def date_count(self) -> int:
        return len(self.dates)

    @property
    def coverage_ratio(self) -> float:
        if self.expected_hour_count == 0:
            return 1.0
        return self.observed_hour_count / self.expected_hour_count

    def to_dict(self) -> dict[str, object]:
        return {
            "place": self.place,
            "timezone": self.timezone,
            "date_count": self.date_count,
            "expected_hour_count": self.expected_hour_count,
            "observed_hour_count": self.observed_hour_count,
            "missing_hour_count": self.missing_hour_count,
            "coverage_ratio": self.coverage_ratio,
            "gap_date_count": self.gap_date_count,
            "dates": [date.to_dict() for date in self.dates],
        }


@dataclass(frozen=True)
class CollectionGapReport:
    db_path: Path
    generated_at_utc: str
    configured_place_count: int
    expected_hour_count: int
    observed_hour_count: int
    missing_hour_count: int
    gap_date_count: int
    missing_supported_places: tuple[str, ...]
    places: tuple[GapPlaceSummary, ...]

    @property
    def place_count(self) -> int:
        return len(self.places)

    @property
    def date_count(self) -> int:
        return sum(place.date_count for place in self.places)

    @property
    def coverage_ratio(self) -> float:
        if self.expected_hour_count == 0:
            return 1.0
        return self.observed_hour_count / self.expected_hour_count

    def to_dict(self) -> dict[str, object]:
        return {
            "db_path": str(self.db_path),
            "generated_at_utc": self.generated_at_utc,
            "configured_place_count": self.configured_place_count,
            "place_count": self.place_count,
            "date_count": self.date_count,
            "expected_hour_count": self.expected_hour_count,
            "observed_hour_count": self.observed_hour_count,
            "missing_hour_count": self.missing_hour_count,
            "coverage_ratio": self.coverage_ratio,
            "gap_date_count": self.gap_date_count,
            "missing_supported_places": list(self.missing_supported_places),
            "places": [place.to_dict() for place in self.places],
        }


def load_collection_gap_report(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    place: str | None = None,
    now: datetime | None = None,
) -> CollectionGapReport:
    target_db_path = Path(db_path).expanduser().resolve()
    current_time = (now or datetime.now(tz=UTC)).astimezone(UTC)

    with open_connection(target_db_path) as connection:
        initialize_schema(connection)
        rows = list_capture_hour_rows(connection, place=place)

    if not rows:
        raise StudyValidationError("No raw captures were found. Run `weather-study ingest-raw` first.")

    dates_by_place: dict[str, dict[str, set[int]]] = {}
    timezone_by_place: dict[str, str] = {}
    all_dates: set[str] = set()
    for row in rows:
        current_place = str(row["place"])
        local_date = str(row["local_date"])
        dates_by_place.setdefault(current_place, {}).setdefault(local_date, set()).add(int(row["local_hour"]))
        timezone_by_place[current_place] = str(row["timezone"])
        all_dates.add(local_date)

    ordered_all_dates = sorted(all_dates)
    configured_places = tuple(list_supported_study_places()) if place is None else ((place,) if place else ())
    missing_supported_places = tuple(
        candidate for candidate in configured_places if candidate not in dates_by_place
    )
    place_summaries: list[GapPlaceSummary] = []
    total_expected_hour_count = 0
    total_observed_hour_count = 0
    total_missing_hour_count = 0
    total_gap_date_count = 0

    for current_place in sorted(dates_by_place):
        timezone = timezone_by_place[current_place]
        place_dates = dates_by_place[current_place]
        first_local_date = min(place_dates)
        last_local_date = max(place_dates)
        current_local_date = current_time.astimezone(ZoneInfo(timezone)).date().isoformat()
        current_local_hour = current_time.astimezone(ZoneInfo(timezone)).hour

        date_summaries: list[GapDateSummary] = []
        for local_date in ordered_all_dates:
            if local_date < first_local_date or local_date > last_local_date or local_date > current_local_date:
                continue
            observed_hours = tuple(sorted(place_dates.get(local_date, set())))
            expected_start_hour = min(observed_hours) if local_date == first_local_date and observed_hours else 0
            expected_end_hour = current_local_hour if local_date == current_local_date else 23
            if expected_end_hour < expected_start_hour:
                continue
            expected_hours = tuple(range(expected_start_hour, expected_end_hour + 1))
            observed_in_window = tuple(
                hour for hour in observed_hours if expected_start_hour <= hour <= expected_end_hour
            )
            missing_hours = tuple(hour for hour in expected_hours if hour not in observed_in_window)
            date_summaries.append(
                GapDateSummary(
                    local_date=local_date,
                    expected_start_hour=expected_start_hour,
                    expected_end_hour=expected_end_hour,
                    expected_hour_count=len(expected_hours),
                    observed_hour_count=len(observed_in_window),
                    missing_hour_count=len(missing_hours),
                    observed_hours=observed_in_window,
                    missing_hours=missing_hours,
                    is_current_local_date=(local_date == current_local_date),
                )
            )

        expected_hour_count = sum(date.expected_hour_count for date in date_summaries)
        observed_hour_count = sum(date.observed_hour_count for date in date_summaries)
        missing_hour_count = sum(date.missing_hour_count for date in date_summaries)
        gap_date_count = sum(1 for date in date_summaries if date.missing_hour_count > 0)
        place_summaries.append(
            GapPlaceSummary(
                place=current_place,
                timezone=timezone,
                expected_hour_count=expected_hour_count,
                observed_hour_count=observed_hour_count,
                missing_hour_count=missing_hour_count,
                gap_date_count=gap_date_count,
                dates=tuple(date_summaries),
            )
        )
        total_expected_hour_count += expected_hour_count
        total_observed_hour_count += observed_hour_count
        total_missing_hour_count += missing_hour_count
        total_gap_date_count += gap_date_count

    return CollectionGapReport(
        db_path=target_db_path,
        generated_at_utc=current_time.isoformat().replace("+00:00", "Z"),
        configured_place_count=len(configured_places) if configured_places else len(place_summaries),
        expected_hour_count=total_expected_hour_count,
        observed_hour_count=total_observed_hour_count,
        missing_hour_count=total_missing_hour_count,
        gap_date_count=total_gap_date_count,
        missing_supported_places=missing_supported_places,
        places=tuple(place_summaries),
    )
