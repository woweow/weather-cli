from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from weather_study_cli.application.errors import StudyValidationError
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import (
    list_hourly_accuracy_metric_rows,
    list_hourly_market_opportunity_metric_rows,
)
from weather_study_cli.ui import render_accuracy_dashboard_html


@dataclass(frozen=True)
class AccuracyDashboardReport:
    generated_at_utc: str
    min_valid_sample: int
    cities: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at_utc": self.generated_at_utc,
            "min_valid_sample": self.min_valid_sample,
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
        rows = list_hourly_accuracy_metric_rows(connection, place=place)
        market_rows = list_hourly_market_opportunity_metric_rows(connection, place=place)

    if not rows:
        raise StudyValidationError(
            "No hourly accuracy metrics were found. Run `weather-study compute-accuracy-metrics` first."
        )

    grouped: dict[str, list[dict[str, object]]] = {}
    market_by_place: dict[str, list[dict[str, object]]] = {}
    timezone_by_place: dict[str, str] = {}
    for row in rows:
        grouped.setdefault(row["place"], []).append(row)
        timezone_by_place[row["place"]] = str(row["timezone"])
    for row in market_rows:
        market_by_place.setdefault(row["place"], []).append(row)
        timezone_by_place[row["place"]] = str(row["timezone"])

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
        cities.append(
            {
                "place": current_place,
                "timezone": timezone_by_place[current_place],
                "study_day_count": study_day_count,
                "thin_sample_hours": thin_sample_hours,
                "market_thin_sample_hours": market_thin_sample_hours,
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
