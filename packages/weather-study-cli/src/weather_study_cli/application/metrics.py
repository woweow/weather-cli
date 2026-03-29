from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import (
    get_table_counts,
    list_accuracy_actual_rows,
    list_accuracy_capture_rows,
    replace_hourly_accuracy_metrics,
)


@dataclass(frozen=True)
class AccuracyMetricSummary:
    db_path: Path
    place_count: int
    metric_row_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "db_path": str(self.db_path),
            "place_count": self.place_count,
            "metric_row_count": self.metric_row_count,
        }


def compute_accuracy_metrics(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    place: str | None = None,
    now: datetime | None = None,
) -> AccuracyMetricSummary:
    target_db_path = Path(db_path).expanduser().resolve()
    computed_at = (now or datetime.now(tz=UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")

    with open_connection(target_db_path) as connection:
        initialize_schema(connection)
        capture_rows = list_accuracy_capture_rows(connection, place=place)
        actual_rows = list_accuracy_actual_rows(connection, place=place)

        latest_capture_by_day_hour: dict[tuple[str, str, int], dict[str, Any]] = {}
        days_by_place: dict[str, set[str]] = {}
        timezone_by_place: dict[str, str] = {}
        hours_by_place: dict[str, set[int]] = {}

        for row in capture_rows:
            key = (row["place"], row["local_date"], row["local_hour"])
            existing = latest_capture_by_day_hour.get(key)
            if existing is None or row["captured_at_utc"] > existing["captured_at_utc"]:
                latest_capture_by_day_hour[key] = row
            days_by_place.setdefault(row["place"], set()).add(row["local_date"])
            timezone_by_place[row["place"]] = row["timezone"]
            hours_by_place.setdefault(row["place"], set()).add(row["local_hour"])

        actual_by_day = {
            (row["place"], row["local_date"]): row["observed_high_temperature_f"]
            for row in actual_rows
        }

        metrics_by_place: dict[str, list[dict[str, Any]]] = {}
        for current_place, local_dates in days_by_place.items():
            timezone = timezone_by_place[current_place]
            metrics: list[dict[str, Any]] = []
            for local_hour in sorted(hours_by_place.get(current_place, set())):
                valid_day_count = 0
                missing_day_count = 0
                excluded_day_count = 0
                correct_day_count = 0

                for local_date in sorted(local_dates):
                    capture = latest_capture_by_day_hour.get((current_place, local_date, local_hour))
                    if capture is None:
                        missing_day_count += 1
                        continue
                    actual_high = actual_by_day.get((current_place, local_date))
                    forecast_high = capture["forecast_high_f"]
                    if actual_high is None or forecast_high is None:
                        excluded_day_count += 1
                        continue
                    valid_day_count += 1
                    if _round_half_up(actual_high) == _round_half_up(forecast_high):
                        correct_day_count += 1

                accuracy_ratio = correct_day_count / valid_day_count if valid_day_count else 0.0
                metrics.append(
                    {
                        "place": current_place,
                        "timezone": timezone,
                        "local_hour": local_hour,
                        "valid_day_count": valid_day_count,
                        "missing_day_count": missing_day_count,
                        "excluded_day_count": excluded_day_count,
                        "correct_day_count": correct_day_count,
                        "accuracy_ratio": accuracy_ratio,
                        "computed_at_utc": computed_at,
                    }
                )
            metrics_by_place[current_place] = metrics

        for current_place, metrics in metrics_by_place.items():
            replace_hourly_accuracy_metrics(connection, place=current_place, metrics=metrics)
        connection.commit()
        counts = get_table_counts(connection)

    return AccuracyMetricSummary(
        db_path=target_db_path,
        place_count=len(metrics_by_place),
        metric_row_count=counts["hourly_accuracy_metrics"],
    )


def _round_half_up(value: float) -> int:
    return int(value + 0.5)
