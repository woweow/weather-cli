from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from weather_study_cli.application.actuals import (
    DEFAULT_CONTACT_EMAIL,
    DailyActualDerivationSummary,
    ObservedHighService,
    derive_daily_actuals,
)
from weather_study_cli.application.gaps import CollectionGapReport, load_collection_gap_report
from weather_study_cli.application.ingest import IngestSummary, ingest_capture_directory
from weather_study_cli.application.market_metrics import (
    MarketOpportunityMetricSummary,
    compute_market_opportunity_metrics,
)
from weather_study_cli.application.metrics import AccuracyMetricSummary, compute_accuracy_metrics
from weather_study_cli.application.raw_loader import DEFAULT_MOCK_DATA_DIR
from weather_study_cli.application.report import export_accuracy_html, load_accuracy_dashboard_report
from weather_study_cli.application.s3 import (
    DEFAULT_AWS_PROFILE,
    DEFAULT_S3_DOWNLOAD_DIR,
    DEFAULT_S3_PREFIX,
    S3SyncSummary,
    sync_capture_directory_from_s3,
)
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH


DEFAULT_HTML_REPORT_PATH = Path(".study") / "weather-study.html"


@dataclass(frozen=True)
class BuildStudyCitySummary:
    place: str
    timezone: str
    study_day_count: int
    capture_day_count: int
    resolved_actual_day_count: int
    capture_window_start_date: str | None
    capture_window_end_date: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "place": self.place,
            "timezone": self.timezone,
            "study_day_count": self.study_day_count,
            "capture_day_count": self.capture_day_count,
            "resolved_actual_day_count": self.resolved_actual_day_count,
            "capture_window_start_date": self.capture_window_start_date,
            "capture_window_end_date": self.capture_window_end_date,
        }


@dataclass(frozen=True)
class BuildStudyReportSummary:
    input_root: Path
    db_path: Path
    output_path: Path
    sync: S3SyncSummary | None
    ingest: IngestSummary
    actuals: DailyActualDerivationSummary
    accuracy_metrics: AccuracyMetricSummary
    market_metrics: MarketOpportunityMetricSummary
    gaps: CollectionGapReport
    cities: tuple[BuildStudyCitySummary, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "input_root": str(self.input_root),
            "db_path": str(self.db_path),
            "output_path": str(self.output_path),
            "sync": None if self.sync is None else self.sync.to_dict(),
            "ingest": self.ingest.to_dict(),
            "actuals": self.actuals.to_dict(),
            "accuracy_metrics": self.accuracy_metrics.to_dict(),
            "market_metrics": self.market_metrics.to_dict(),
            "gaps": self.gaps.to_dict(),
            "cities": [city.to_dict() for city in self.cities],
        }


def build_study_report(
    *,
    input_path: str | Path = DEFAULT_MOCK_DATA_DIR,
    db_path: str | Path = DEFAULT_DB_PATH,
    output_path: str | Path = DEFAULT_HTML_REPORT_PATH,
    place: str | None = None,
    min_valid_sample: int = 5,
    bucket: str | None = None,
    prefix: str = DEFAULT_S3_PREFIX,
    sync_output_root: str | Path = DEFAULT_S3_DOWNLOAD_DIR,
    profile: str | None = DEFAULT_AWS_PROFILE,
    delete: bool = False,
    validate_sync: bool = True,
    contact_email: str = DEFAULT_CONTACT_EMAIL,
    weather_service: ObservedHighService | None = None,
) -> BuildStudyReportSummary:
    sync_summary: S3SyncSummary | None = None
    source_input = Path(input_path).expanduser().resolve()
    if bucket is not None:
        sync_summary = sync_capture_directory_from_s3(
            bucket,
            prefix=prefix,
            output_root=sync_output_root,
            profile=profile,
            delete=delete,
            validate=validate_sync,
        )
        source_input = sync_summary.output_root

    ingest_summary = ingest_capture_directory(source_input, db_path=db_path, reset=True)
    actuals_summary = derive_daily_actuals(
        db_path=db_path,
        place=place,
        contact_email=contact_email,
        weather_service=weather_service,
    )
    accuracy_summary = compute_accuracy_metrics(db_path=db_path, place=place)
    market_summary = compute_market_opportunity_metrics(db_path=db_path, place=place)
    gap_summary = load_collection_gap_report(db_path=db_path, place=place)

    target_output = Path(output_path).expanduser().resolve()
    export_accuracy_html(
        db_path=db_path,
        output_path=target_output,
        place=place,
        min_valid_sample=min_valid_sample,
    )
    report = load_accuracy_dashboard_report(
        db_path=db_path,
        place=place,
        min_valid_sample=min_valid_sample,
    )
    city_summaries = tuple(
        BuildStudyCitySummary(
            place=str(city["place"]),
            timezone=str(city["timezone"]),
            study_day_count=int(city["study_day_count"]),
            capture_day_count=int(city["capture_day_count"]),
            resolved_actual_day_count=int(city["resolved_actual_day_count"]),
            capture_window_start_date=(
                None
                if city["capture_window_start_date"] is None
                else str(city["capture_window_start_date"])
            ),
            capture_window_end_date=(
                None
                if city["capture_window_end_date"] is None
                else str(city["capture_window_end_date"])
            ),
        )
        for city in report.cities
    )

    return BuildStudyReportSummary(
        input_root=source_input,
        db_path=Path(db_path).expanduser().resolve(),
        output_path=target_output,
        sync=sync_summary,
        ingest=ingest_summary,
        actuals=actuals_summary,
        accuracy_metrics=accuracy_summary,
        market_metrics=market_summary,
        gaps=gap_summary,
        cities=city_summaries,
    )
