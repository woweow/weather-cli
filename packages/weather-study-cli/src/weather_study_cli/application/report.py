from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from weather_study_cli.application.errors import StudyValidationError
from weather_study_cli.application.market_utils import find_winning_market_row
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import (
    list_accuracy_actual_rows,
    list_daily_actual_targets,
    list_hourly_accuracy_metric_rows,
    list_market_capture_rows,
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
        capture_rows = list_market_capture_rows(connection, place=place)
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

    day_targets_by_place: dict[str, list[dict[str, str]]] = defaultdict(list)
    for target in day_targets:
        day_targets_by_place[str(target["place"])].append(target)
        timezone_by_place[str(target["place"])] = str(target["timezone"])

    actual_dates_by_place: dict[str, set[str]] = defaultdict(set)
    for row in actual_rows:
        actual_dates_by_place[str(row["place"])].add(str(row["local_date"]))

    market_annotations = _build_market_annotations(capture_rows=capture_rows, actual_rows=actual_rows)
    cities: list[dict[str, object]] = []
    for current_place, rows in sorted(grouped_accuracy.items()):
        ordered_rows = sorted(rows, key=lambda item: int(item["local_hour"]))
        local_dates = sorted(str(target["local_date"]) for target in day_targets_by_place.get(current_place, ()))
        annotation_by_hour = market_annotations.get(current_place, {})
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
            annotation = annotation_by_hour.get(local_hour, {})
            valid_day_count = int(row["valid_day_count"])
            points.append(
                {
                    "local_hour": local_hour,
                    "accuracy_ratio": float(row["accuracy_ratio"]),
                    "valid_day_count": valid_day_count,
                    "missing_day_count": int(row["missing_day_count"]),
                    "excluded_day_count": int(row["excluded_day_count"]),
                    "correct_day_count": int(row["correct_day_count"]),
                    "thin_sample": valid_day_count < min_valid_sample,
                    "winning_market_label": annotation.get("winning_market_label"),
                    "avg_winning_bucket_last_price_cents": annotation.get(
                        "avg_winning_bucket_last_price_cents"
                    ),
                    "winning_market_sample_count": int(annotation.get("winning_market_sample_count", 0)),
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


def _build_market_annotations(
    *,
    capture_rows: list[dict[str, Any]],
    actual_rows: list[dict[str, Any]],
) -> dict[str, dict[int, dict[str, object]]]:
    latest_capture_by_day_hour: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in capture_rows:
        key = (str(row["place"]), str(row["local_date"]), int(row["local_hour"]))
        existing = latest_capture_by_day_hour.get(key)
        if existing is None or str(row["captured_at_utc"]) > str(existing["captured_at_utc"]):
            latest_capture_by_day_hour[key] = row

    actual_by_day = {
        (str(row["place"]), str(row["local_date"])): float(row["observed_high_temperature_f"])
        for row in actual_rows
    }
    grouped: dict[str, dict[int, list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))

    for (place, local_date, local_hour), row in latest_capture_by_day_hour.items():
        actual_high = actual_by_day.get((place, local_date))
        if actual_high is None:
            continue
        payload = json.loads(str(row["capture_json"]))
        market_payload = payload.get("market", {}).get("payload")
        market_rows = tuple(market_payload.get("markets", [])) if market_payload else ()
        if not market_rows:
            continue
        winning_market = find_winning_market_row(market_rows, actual_high)
        if winning_market is None:
            continue
        grouped[place][local_hour].append(
            {
                "label": str(winning_market.get("label") or ""),
                "last_price_cents": winning_market.get("last_price_cents"),
            }
        )

    annotations: dict[str, dict[int, dict[str, object]]] = {}
    for place, by_hour in grouped.items():
        annotations[place] = {}
        for local_hour, entries in by_hour.items():
            labels = [str(entry["label"]) for entry in entries if entry.get("label")]
            prices = [
                float(entry["last_price_cents"])
                for entry in entries
                if entry.get("last_price_cents") is not None
            ]
            label_counter = Counter(labels)
            winning_market_label = None
            if label_counter:
                winning_market_label = sorted(
                    label_counter.items(),
                    key=lambda item: (-item[1], item[0]),
                )[0][0]
            annotations[place][local_hour] = {
                "winning_market_label": winning_market_label,
                "avg_winning_bucket_last_price_cents": (sum(prices) / len(prices)) if prices else None,
                "winning_market_sample_count": len(entries),
            }
    return annotations
