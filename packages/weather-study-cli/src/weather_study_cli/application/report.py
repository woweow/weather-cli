from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from weather_study_cli.application.errors import StudyValidationError
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import (
    list_accuracy_actual_rows,
    list_daily_actual_targets,
    list_hourly_accuracy_metric_rows,
    list_hourly_market_opportunity_metric_rows,
)
from weather_study_cli.ui import render_accuracy_dashboard_html


@dataclass(frozen=True)
class AccuracyDashboardReport:
    generated_at_utc: str
    min_valid_sample: int
    missing_supported_places: tuple[str, ...]
    cities: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at_utc": self.generated_at_utc,
            "min_valid_sample": self.min_valid_sample,
            "missing_supported_places": list(self.missing_supported_places),
            "cities": list(self.cities),
        }


def load_accuracy_dashboard_report(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    place: str | None = None,
    min_valid_sample: int = 5,
) -> AccuracyDashboardReport:
    target_db_path = Path(db_path).expanduser().resolve()
    with open_connection(target_db_path) as connection:
        initialize_schema(connection)
        accuracy_rows = list_hourly_accuracy_metric_rows(connection, place=place)
        market_rows = list_hourly_market_opportunity_metric_rows(connection, place=place)
        actual_rows = list_accuracy_actual_rows(connection, place=place)
        day_targets = list_daily_actual_targets(connection, place=place)

    if not accuracy_rows:
        raise StudyValidationError(
            "No hourly accuracy metrics were found. Run `weather-study compute-accuracy-metrics` first."
        )

    grouped_accuracy: dict[str, list[dict[str, object]]] = defaultdict(list)
    timezone_by_place: dict[str, str] = {}
    for row in accuracy_rows:
        grouped_accuracy[str(row["place"])].append(row)
        timezone_by_place[str(row["place"])] = str(row["timezone"])

    market_by_place_hour: dict[tuple[str, int], dict[str, Any]] = {}
    for row in market_rows:
        market_by_place_hour[(str(row["place"]), int(row["local_hour"]))] = row

    day_targets_by_place: dict[str, list[dict[str, str]]] = defaultdict(list)
    for target in day_targets:
        day_targets_by_place[str(target["place"])].append(target)
        timezone_by_place[str(target["place"])] = str(target["timezone"])

    actual_dates_by_place: dict[str, set[str]] = defaultdict(set)
    for row in actual_rows:
        actual_dates_by_place[str(row["place"])].add(str(row["local_date"]))

    cities: list[dict[str, object]] = []
    for current_place, rows in sorted(grouped_accuracy.items()):
        ordered_rows = sorted(rows, key=lambda item: int(item["local_hour"]))
        local_dates = sorted(str(target["local_date"]) for target in day_targets_by_place.get(current_place, ()))
        best_row = max(
            ordered_rows,
            key=lambda item: (
                float(item["accuracy_ratio"]),
                -int(item["local_hour"]),
            ),
        )
        points = []
        for row in ordered_rows:
            local_hour = int(row["local_hour"])
            valid_day_count = int(row["valid_day_count"])
            mrow = market_by_place_hour.get((current_place, local_hour), {})
            avg_price = mrow.get("avg_winning_bucket_last_price_cents")
            points.append(
                {
                    "local_hour": local_hour,
                    "accuracy_ratio": float(row["accuracy_ratio"]),
                    "valid_day_count": valid_day_count,
                    "missing_day_count": int(row["missing_day_count"]),
                    "excluded_day_count": int(row["excluded_day_count"]),
                    "correct_day_count": int(row["correct_day_count"]),
                    "thin_sample": valid_day_count < min_valid_sample,
                    "winning_market_label": None,
                    "avg_winning_bucket_last_price_cents": avg_price,
                    "winning_market_sample_count": int(mrow.get("valid_day_count", 0)),
                }
            )

        cities.append(
            {
                "place": current_place,
                "timezone": timezone_by_place[current_place],
                "study_day_count": max(
                    int(row["valid_day_count"]) + int(row["missing_day_count"]) + int(row["excluded_day_count"])
                    for row in ordered_rows
                ),
                "capture_day_count": len(local_dates),
                "resolved_actual_day_count": len(actual_dates_by_place.get(current_place, set())),
                "capture_window_start_date": None if not local_dates else min(local_dates),
                "capture_window_end_date": None if not local_dates else max(local_dates),
                "best_hour": int(best_row["local_hour"]),
                "best_accuracy_ratio": float(best_row["accuracy_ratio"]),
                "points": points,
            }
        )

    return AccuracyDashboardReport(
        generated_at_utc=datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        min_valid_sample=min_valid_sample,
        missing_supported_places=(),
        cities=tuple(cities),
    )


def export_accuracy_html(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    output_path: str | Path | None = None,
    place: str | None = None,
    min_valid_sample: int = 5,
) -> int:
    report = load_accuracy_dashboard_report(
        db_path=db_path,
        place=place,
        min_valid_sample=min_valid_sample,
    )
    html = render_accuracy_dashboard_html(report.to_dict())
    if output_path:
        target = Path(output_path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
    else:
        sys.stdout.write(html)
    return 0
