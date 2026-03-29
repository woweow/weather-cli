from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from weather_study_cli.application.raw_loader import load_capture_directory
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema, reset_database_file
from weather_study_cli.persistence.repository import (
    get_table_counts,
    replace_capture_rows,
    upsert_raw_capture,
)


@dataclass(frozen=True)
class IngestSummary:
    input_root: Path
    db_path: Path
    ingested_capture_count: int
    raw_capture_count: int
    forecast_period_count: int
    market_row_count: int
    daily_actual_count: int
    hourly_accuracy_metric_count: int
    hourly_market_opportunity_metric_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "input_root": str(self.input_root),
            "db_path": str(self.db_path),
            "ingested_capture_count": self.ingested_capture_count,
            "raw_capture_count": self.raw_capture_count,
            "forecast_period_count": self.forecast_period_count,
            "market_row_count": self.market_row_count,
            "daily_actual_count": self.daily_actual_count,
            "hourly_accuracy_metric_count": self.hourly_accuracy_metric_count,
            "hourly_market_opportunity_metric_count": self.hourly_market_opportunity_metric_count,
        }


def ingest_capture_directory(
    input_path: str | Path,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    reset: bool = False,
) -> IngestSummary:
    raw_summary = load_capture_directory(input_path)
    target_db_path = Path(db_path).expanduser().resolve()

    if reset:
        reset_database_file(target_db_path)

    with open_connection(target_db_path) as connection:
        initialize_schema(connection)
        for capture in raw_summary.captures:
            capture_id = upsert_raw_capture(connection, capture)
            replace_capture_rows(connection, capture_id, capture)
        connection.commit()
        counts = get_table_counts(connection)

    return IngestSummary(
        input_root=raw_summary.root,
        db_path=target_db_path,
        ingested_capture_count=raw_summary.file_count,
        raw_capture_count=counts["raw_captures"],
        forecast_period_count=counts["forecast_periods"],
        market_row_count=counts["market_rows"],
        daily_actual_count=counts["daily_actuals"],
        hourly_accuracy_metric_count=counts["hourly_accuracy_metrics"],
        hourly_market_opportunity_metric_count=counts["hourly_market_opportunity_metrics"],
    )
