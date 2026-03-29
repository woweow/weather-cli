from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from weather_study_cli.application.day_report import load_day_drilldown_report
from weather_study_cli.application.errors import StudyValidationError
from weather_study_cli.application.gaps import load_collection_gap_report
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import (
    list_daily_actual_targets,
    list_hourly_accuracy_metric_rows,
    list_hourly_market_opportunity_metric_rows,
)
from weather_study_cli.ui import render_accuracy_dashboard_html

ACCURACY_THRESHOLDS = (0.6, 0.7, 0.8, 0.9)


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


def _build_threshold_summary(
    *,
    accuracy_rows: list[dict[str, object]],
    market_rows: list[dict[str, object]],
    min_valid_sample: int,
) -> list[dict[str, object]]:
    resolved_rows = [
        row for row in accuracy_rows if int(row["valid_day_count"]) > 0
    ]
    market_by_hour = {
        int(row["local_hour"]): row
        for row in market_rows
    }
    best_resolved_row = max(
        resolved_rows,
        key=lambda row: (
            float(row["accuracy_ratio"]),
            -int(row["local_hour"]),
        ),
        default=None,
    )
    summary: list[dict[str, object]] = []

    for threshold_ratio in ACCURACY_THRESHOLDS:
        threshold_label = f"{int(threshold_ratio * 100)}%"
        reached_row = next(
            (
                row
                for row in accuracy_rows
                if int(row["valid_day_count"]) > 0
                and float(row["accuracy_ratio"]) >= threshold_ratio
            ),
            None,
        )
        if reached_row is None:
            summary.append(
                {
                    "threshold_ratio": threshold_ratio,
                    "threshold_label": threshold_label,
                    "status": "unresolved" if not resolved_rows else "not_reached",
                    "best_resolved_hour": (
                        None if best_resolved_row is None else int(best_resolved_row["local_hour"])
                    ),
                    "best_accuracy_ratio": (
                        None if best_resolved_row is None else float(best_resolved_row["accuracy_ratio"])
                    ),
                    "best_valid_day_count": (
                        None if best_resolved_row is None else int(best_resolved_row["valid_day_count"])
                    ),
                    "best_correct_day_count": (
                        None if best_resolved_row is None else int(best_resolved_row["correct_day_count"])
                    ),
                }
            )
            continue

        hour = int(reached_row["local_hour"])
        market_row = market_by_hour.get(hour)
        summary.append(
            {
                "threshold_ratio": threshold_ratio,
                "threshold_label": threshold_label,
                "status": "reached",
                "local_hour": hour,
                "accuracy_ratio": float(reached_row["accuracy_ratio"]),
                "valid_day_count": int(reached_row["valid_day_count"]),
                "correct_day_count": int(reached_row["correct_day_count"]),
                "thin_sample": int(reached_row["valid_day_count"]) < min_valid_sample,
                "market_summary": (
                    None
                    if market_row is None
                    else {
                        "valid_day_count": int(market_row["valid_day_count"]),
                        "leader_match_day_count": int(market_row["leader_match_day_count"]),
                        "leader_match_ratio": float(market_row["leader_match_ratio"]),
                        "avg_winning_bucket_last_price_cents": (
                            None
                            if market_row["avg_winning_bucket_last_price_cents"] is None
                            else float(market_row["avg_winning_bucket_last_price_cents"])
                        ),
                    }
                ),
            }
        )

    return summary


def load_accuracy_dashboard_report(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    place: str | None = None,
    min_valid_sample: int = 5,
) -> AccuracyDashboardReport:
    target_db_path = Path(db_path).expanduser().resolve()
    with open_connection(target_db_path) as connection:
        initialize_schema(connection)
        rows = list_hourly_accuracy_metric_rows(connection, place=place)
        market_rows = list_hourly_market_opportunity_metric_rows(connection, place=place)
        day_targets = list_daily_actual_targets(connection, place=place)
    gap_report = load_collection_gap_report(db_path=target_db_path, place=place)

    if not rows:
        raise StudyValidationError(
            "No hourly accuracy metrics were found. Run `weather-study compute-accuracy-metrics` first."
        )

    grouped: dict[str, list[dict[str, object]]] = {}
    market_by_place: dict[str, list[dict[str, object]]] = {}
    day_targets_by_place: dict[str, list[dict[str, str]]] = {}
    gap_by_place = {place_summary.place: place_summary.to_dict() for place_summary in gap_report.places}
    timezone_by_place: dict[str, str] = {}
    for row in rows:
        grouped.setdefault(row["place"], []).append(row)
        timezone_by_place[row["place"]] = str(row["timezone"])
    for row in market_rows:
        market_by_place.setdefault(row["place"], []).append(row)
        timezone_by_place[row["place"]] = str(row["timezone"])
    for target in day_targets:
        day_targets_by_place.setdefault(target["place"], []).append(target)
        timezone_by_place[target["place"]] = str(target["timezone"])

    cities = []
    for current_place, current_rows in sorted(grouped.items()):
        ordered_rows = sorted(current_rows, key=lambda item: int(item["local_hour"]))
        ordered_market_rows = sorted(
            market_by_place.get(current_place, ()),
            key=lambda item: int(item["local_hour"]),
        )
        study_day_count = max(
            int(row["valid_day_count"]) + int(row["missing_day_count"]) + int(row["excluded_day_count"])
            for row in ordered_rows
        )
        thin_sample_hours = [
            int(row["local_hour"])
            for row in ordered_rows
            if int(row["valid_day_count"]) < min_valid_sample
        ]
        market_thin_sample_hours = [
            int(row["local_hour"])
            for row in ordered_market_rows
            if int(row["valid_day_count"]) < min_valid_sample
        ]
        day_drilldowns = [
            load_day_drilldown_report(
                db_path=target_db_path,
                place=current_place,
                local_date=str(target["local_date"]),
            ).to_dict()
            for target in sorted(
                day_targets_by_place.get(current_place, ()),
                key=lambda item: str(item["local_date"]),
                reverse=True,
            )
        ]
        local_dates = [str(target["local_date"]) for target in day_targets_by_place.get(current_place, ())]
        cities.append(
            {
                "place": current_place,
                "timezone": timezone_by_place[current_place],
                "study_day_count": study_day_count,
                "capture_day_count": len(local_dates),
                "resolved_actual_day_count": sum(
                    1
                    for day in day_drilldowns
                    if day["actual_high_temperature_f"] is not None
                ),
                "capture_window_start_date": (None if not local_dates else min(local_dates)),
                "capture_window_end_date": (None if not local_dates else max(local_dates)),
                "thin_sample_hours": thin_sample_hours,
                "market_thin_sample_hours": market_thin_sample_hours,
                "gap_summary": gap_by_place.get(current_place),
                "day_drilldowns": day_drilldowns,
                "threshold_summary": _build_threshold_summary(
                    accuracy_rows=ordered_rows,
                    market_rows=ordered_market_rows,
                    min_valid_sample=min_valid_sample,
                ),
                "points": [
                    {
                        "local_hour": int(row["local_hour"]),
                        "accuracy_ratio": float(row["accuracy_ratio"]),
                        "valid_day_count": int(row["valid_day_count"]),
                        "missing_day_count": int(row["missing_day_count"]),
                        "excluded_day_count": int(row["excluded_day_count"]),
                        "correct_day_count": int(row["correct_day_count"]),
                    }
                    for row in ordered_rows
                ],
                "market_points": [
                    {
                        "local_hour": int(row["local_hour"]),
                        "leader_match_ratio": float(row["leader_match_ratio"]),
                        "valid_day_count": int(row["valid_day_count"]),
                        "missing_day_count": int(row["missing_day_count"]),
                        "excluded_day_count": int(row["excluded_day_count"]),
                        "leader_match_day_count": int(row["leader_match_day_count"]),
                        "avg_winning_bucket_last_price_cents": (
                            None
                            if row["avg_winning_bucket_last_price_cents"] is None
                            else float(row["avg_winning_bucket_last_price_cents"])
                        ),
                    }
                    for row in ordered_market_rows
                ],
            }
        )

    return AccuracyDashboardReport(
        generated_at_utc=datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        min_valid_sample=min_valid_sample,
        missing_supported_places=gap_report.missing_supported_places,
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
