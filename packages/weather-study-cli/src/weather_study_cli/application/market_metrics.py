from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from weather_study_cli.application.forecast_accuracy_spec import spec_day_hour_metrics_bundle
from weather_study_cli.application.market_utils import find_winning_market_row, select_market_leader
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import (
    get_table_counts,
    list_daily_actuals_with_observed_payload,
    list_forecast_period_rows_for_captures,
    list_latest_raw_capture_stubs,
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
        stubs = list_latest_raw_capture_stubs(connection, place=place)
        if not stubs:
            metrics_by_place: dict[str, list[dict[str, Any]]] = {}
        else:
            cap_ids = tuple(sorted({s["raw_capture_id"] for s in stubs}))
            fp_rows = list_forecast_period_rows_for_captures(connection, raw_capture_ids=cap_ids)
            periods_by_capture: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for row in fp_rows:
                periods_by_capture[int(row["raw_capture_id"])].append(
                    {
                        "start": row["start"],
                        "end": row["end"],
                        "temperature_f": row["temperature_f"],
                    }
                )
            actual_rows = list_daily_actuals_with_observed_payload(connection, place=place)
            actual_by_day = {(r["place"], r["local_date"]): r for r in actual_rows}
            days_by_place: dict[str, set[str]] = defaultdict(set)
            hours_by_place: dict[str, set[int]] = defaultdict(set)
            timezone_by_place: dict[str, str] = {}
            stub_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
            for s in stubs:
                p = str(s["place"])
                ld = str(s["local_date"])
                lh = int(s["local_hour"])
                days_by_place[p].add(ld)
                hours_by_place[p].add(lh)
                timezone_by_place[p] = str(s["timezone"])
                stub_by_key[(p, ld, lh)] = s

            metrics_by_place = {}
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
                        stub = stub_by_key.get((current_place, local_date, local_hour))
                        if stub is None:
                            missing_day_count += 1
                            continue
                        actual_row = actual_by_day.get((current_place, local_date))
                        if actual_row is None:
                            excluded_day_count += 1
                            continue
                        fc_rows = tuple(periods_by_capture.get(int(stub["raw_capture_id"]), ()))
                        eligible, _correct, price = spec_day_hour_metrics_bundle(
                            timezone=timezone,
                            local_date=local_date,
                            local_hour=local_hour,
                            observed_high_temperature_f=(
                                float(actual_row["observed_high_temperature_f"])
                                if actual_row.get("observed_high_temperature_f") is not None
                                else None
                            ),
                            observed_payload=actual_row.get("observed_payload"),
                            local_timestamp=str(stub["local_timestamp"]),
                            forecast_rows=fc_rows,
                            capture_json=str(stub["capture_json"]),
                        )
                        if not eligible or price is None:
                            excluded_day_count += 1
                            continue
                        valid_day_count += 1
                        winning_bucket_last_prices.append(price)
                        try:
                            payload = json.loads(str(stub["capture_json"]))
                        except json.JSONDecodeError:
                            continue
                        market_payload = payload.get("market", {}).get("payload")
                        market_rows = tuple(market_payload.get("markets", [])) if market_payload else ()
                        if not market_rows:
                            continue
                        ah = actual_row.get("observed_high_temperature_f")
                        if ah is None:
                            continue
                        winning_market = find_winning_market_row(market_rows, float(ah))
                        market_leader = select_market_leader(market_rows)
                        if (
                            winning_market is not None
                            and market_leader is not None
                            and market_leader.get("ticker") == winning_market.get("ticker")
                        ):
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
