from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from weather_study_cli.application.market_utils import find_winning_market_row, select_market_leader
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import (
    get_table_counts,
    list_accuracy_actual_rows,
    list_market_capture_rows,
    replace_hourly_market_opportunity_metrics,
)


@dataclass(frozen=True)
class MarketOpportunityMetricSummary:
    db_path: Path
    place_count: int
    metric_row_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "db_path": str(self.db_path),
            "place_count": self.place_count,
            "metric_row_count": self.metric_row_count,
        }


def compute_market_opportunity_metrics(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    place: str | None = None,
    now: datetime | None = None,
) -> MarketOpportunityMetricSummary:
    target_db_path = Path(db_path).expanduser().resolve()
    computed_at = (now or datetime.now(tz=UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")

    with open_connection(target_db_path) as connection:
        initialize_schema(connection)
        capture_rows = list_market_capture_rows(connection, place=place)
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
                leader_match_day_count = 0
                winning_bucket_last_prices: list[int] = []

                for local_date in sorted(local_dates):
                    capture = latest_capture_by_day_hour.get((current_place, local_date, local_hour))
                    if capture is None:
                        missing_day_count += 1
                        continue

                    actual_high = actual_by_day.get((current_place, local_date))
                    if actual_high is None:
                        excluded_day_count += 1
                        continue

                    payload = json.loads(str(capture["capture_json"]))
                    market_payload = payload.get("market", {}).get("payload")
                    market_rows = tuple(market_payload.get("markets", [])) if market_payload else ()
                    if not market_rows:
                        excluded_day_count += 1
                        continue

                    winning_market = find_winning_market_row(market_rows, actual_high)
                    if winning_market is None:
                        excluded_day_count += 1
                        continue

                    valid_day_count += 1
                    if winning_market.get("last_price_cents") is not None:
                        winning_bucket_last_prices.append(int(winning_market["last_price_cents"]))
                    market_leader = select_market_leader(market_rows)
                    if market_leader is not None and market_leader.get("ticker") == winning_market.get("ticker"):
                        leader_match_day_count += 1

                leader_match_ratio = leader_match_day_count / valid_day_count if valid_day_count else 0.0
                avg_winning_bucket_last_price_cents = (
                    sum(winning_bucket_last_prices) / len(winning_bucket_last_prices)
                    if winning_bucket_last_prices
                    else None
                )
                metrics.append(
                    {
                        "place": current_place,
                        "timezone": timezone,
                        "local_hour": local_hour,
                        "valid_day_count": valid_day_count,
                        "missing_day_count": missing_day_count,
                        "excluded_day_count": excluded_day_count,
                        "leader_match_day_count": leader_match_day_count,
                        "leader_match_ratio": leader_match_ratio,
                        "avg_winning_bucket_last_price_cents": avg_winning_bucket_last_price_cents,
                        "computed_at_utc": computed_at,
                    }
                )
            metrics_by_place[current_place] = metrics

        for current_place, metrics in metrics_by_place.items():
            replace_hourly_market_opportunity_metrics(connection, place=current_place, metrics=metrics)
        connection.commit()
        counts = get_table_counts(connection)

    return MarketOpportunityMetricSummary(
        db_path=target_db_path,
        place_count=len(metrics_by_place),
        metric_row_count=counts["hourly_market_opportunity_metrics"],
    )
