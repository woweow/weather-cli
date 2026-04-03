from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weather_study_cli.application.actuals import (
        DEFAULT_CONTACT_EMAIL,
        DailyActualDerivationSummary,
        derive_daily_actuals,
    )
    from weather_study_cli.application.day_report import (
        DayCaptureDrilldown,
        StudyDayDrilldownReport,
        load_day_drilldown_report,
    )
    from weather_study_cli.application.cities import (
        SUPPORTED_STUDY_CITIES,
        StudyCity,
        list_supported_study_places,
        resolve_study_cities,
    )
    from weather_study_cli.application.errors import (
        DailyActualDerivationError,
        IncompatibleStudyDatabaseError,
        S3SyncError,
        StudyValidationError,
        WeatherStudyCliError,
    )
    from weather_study_cli.application.gaps import CollectionGapReport, load_collection_gap_report
    from weather_study_cli.application.ingest import IngestSummary, ingest_capture_directory
    from weather_study_cli.application.market_metrics import (
        MarketOpportunityMetricSummary,
        compute_market_opportunity_metrics,
    )
    from weather_study_cli.application.metrics import AccuracyMetricSummary, compute_accuracy_metrics
    from weather_study_cli.application.pipeline import (
        DEFAULT_HTML_REPORT_PATH,
        BuildStudyReportSummary,
        build_study_report,
    )
    from weather_study_cli.application.raw_loader import (
        DEFAULT_MOCK_DATA_DIR,
        StudyDatasetSummary,
        build_capture_relative_path,
        load_capture_directory,
        load_capture_file,
    )
    from weather_study_cli.application.raw_schema import StudyCapture
    from weather_study_cli.application.report import AccuracyDashboardReport, export_accuracy_html
    from weather_study_cli.application.sample_data import (
        DEFAULT_SAMPLE_DAY_COUNT,
        DEFAULT_SAMPLE_METADATA_PATH,
        DEFAULT_SAMPLE_OUTPUT_ROOT,
        DEFAULT_SAMPLE_PLACES,
        DEFAULT_SAMPLE_S3_PREFIX,
        SampleDataGenerationSummary,
        generate_sample_capture_directory,
    )
    from weather_study_cli.application.s3 import (
        DEFAULT_AWS_PROFILE,
        DEFAULT_S3_DOWNLOAD_DIR,
        DEFAULT_S3_PREFIX,
        S3SyncSummary,
        sync_capture_directory_from_s3,
    )
    from weather_study_cli.persistence.connection import DEFAULT_DB_PATH


__all__ = [
    "DEFAULT_AWS_PROFILE",
    "DEFAULT_DB_PATH",
    "DEFAULT_CONTACT_EMAIL",
    "DEFAULT_MOCK_DATA_DIR",
    "DEFAULT_S3_DOWNLOAD_DIR",
    "DEFAULT_S3_PREFIX",
    "DEFAULT_SAMPLE_DAY_COUNT",
    "DEFAULT_SAMPLE_METADATA_PATH",
    "DEFAULT_SAMPLE_OUTPUT_ROOT",
    "DEFAULT_SAMPLE_PLACES",
    "DEFAULT_SAMPLE_S3_PREFIX",
    "AccuracyMetricSummary",
    "AccuracyDashboardReport",
    "CollectionGapReport",
    "DailyActualDerivationError",
    "DailyActualDerivationSummary",
    "DayCaptureDrilldown",
    "DEFAULT_HTML_REPORT_PATH",
    "IncompatibleStudyDatabaseError",
    "IngestSummary",
    "MarketOpportunityMetricSummary",
    "BuildStudyReportSummary",
    "SUPPORTED_STUDY_CITIES",
    "S3SyncError",
    "S3SyncSummary",
    "SampleDataGenerationSummary",
    "StudyCapture",
    "StudyCity",
    "StudyDatasetSummary",
    "StudyDayDrilldownReport",
    "StudyValidationError",
    "WeatherStudyCliError",
    "build_capture_relative_path",
    "derive_daily_actuals",
    "compute_accuracy_metrics",
    "compute_market_opportunity_metrics",
    "build_study_report",
    "ingest_capture_directory",
    "export_accuracy_html",
    "generate_sample_capture_directory",
    "list_supported_study_places",
    "load_collection_gap_report",
    "load_capture_directory",
    "load_capture_file",
    "load_day_drilldown_report",
    "resolve_study_cities",
    "sync_capture_directory_from_s3",
]


_EXPORTS = {
    "DEFAULT_AWS_PROFILE": ("weather_study_cli.application.s3", "DEFAULT_AWS_PROFILE"),
    "DEFAULT_DB_PATH": ("weather_study_cli.persistence.connection", "DEFAULT_DB_PATH"),
    "DEFAULT_CONTACT_EMAIL": ("weather_study_cli.application.actuals", "DEFAULT_CONTACT_EMAIL"),
    "DEFAULT_HTML_REPORT_PATH": ("weather_study_cli.application.pipeline", "DEFAULT_HTML_REPORT_PATH"),
    "DEFAULT_MOCK_DATA_DIR": ("weather_study_cli.application.raw_loader", "DEFAULT_MOCK_DATA_DIR"),
    "DEFAULT_S3_DOWNLOAD_DIR": ("weather_study_cli.application.s3", "DEFAULT_S3_DOWNLOAD_DIR"),
    "DEFAULT_S3_PREFIX": ("weather_study_cli.application.s3", "DEFAULT_S3_PREFIX"),
    "DEFAULT_SAMPLE_DAY_COUNT": ("weather_study_cli.application.sample_data", "DEFAULT_SAMPLE_DAY_COUNT"),
    "DEFAULT_SAMPLE_METADATA_PATH": (
        "weather_study_cli.application.sample_data",
        "DEFAULT_SAMPLE_METADATA_PATH",
    ),
    "DEFAULT_SAMPLE_OUTPUT_ROOT": (
        "weather_study_cli.application.sample_data",
        "DEFAULT_SAMPLE_OUTPUT_ROOT",
    ),
    "DEFAULT_SAMPLE_PLACES": ("weather_study_cli.application.sample_data", "DEFAULT_SAMPLE_PLACES"),
    "DEFAULT_SAMPLE_S3_PREFIX": ("weather_study_cli.application.sample_data", "DEFAULT_SAMPLE_S3_PREFIX"),
    "AccuracyMetricSummary": ("weather_study_cli.application.metrics", "AccuracyMetricSummary"),
    "AccuracyDashboardReport": ("weather_study_cli.application.report", "AccuracyDashboardReport"),
    "CollectionGapReport": ("weather_study_cli.application.gaps", "CollectionGapReport"),
    "BuildStudyReportSummary": ("weather_study_cli.application.pipeline", "BuildStudyReportSummary"),
    "DailyActualDerivationError": ("weather_study_cli.application.errors", "DailyActualDerivationError"),
    "DailyActualDerivationSummary": ("weather_study_cli.application.actuals", "DailyActualDerivationSummary"),
    "DayCaptureDrilldown": ("weather_study_cli.application.day_report", "DayCaptureDrilldown"),
    "IncompatibleStudyDatabaseError": (
        "weather_study_cli.application.errors",
        "IncompatibleStudyDatabaseError",
    ),
    "IngestSummary": ("weather_study_cli.application.ingest", "IngestSummary"),
    "MarketOpportunityMetricSummary": (
        "weather_study_cli.application.market_metrics",
        "MarketOpportunityMetricSummary",
    ),
    "SUPPORTED_STUDY_CITIES": ("weather_study_cli.application.cities", "SUPPORTED_STUDY_CITIES"),
    "S3SyncError": ("weather_study_cli.application.errors", "S3SyncError"),
    "S3SyncSummary": ("weather_study_cli.application.s3", "S3SyncSummary"),
    "SampleDataGenerationSummary": (
        "weather_study_cli.application.sample_data",
        "SampleDataGenerationSummary",
    ),
    "StudyCapture": ("weather_study_cli.application.raw_schema", "StudyCapture"),
    "StudyCity": ("weather_study_cli.application.cities", "StudyCity"),
    "StudyDatasetSummary": ("weather_study_cli.application.raw_loader", "StudyDatasetSummary"),
    "StudyDayDrilldownReport": ("weather_study_cli.application.day_report", "StudyDayDrilldownReport"),
    "StudyValidationError": ("weather_study_cli.application.errors", "StudyValidationError"),
    "WeatherStudyCliError": ("weather_study_cli.application.errors", "WeatherStudyCliError"),
    "build_capture_relative_path": (
        "weather_study_cli.application.raw_loader",
        "build_capture_relative_path",
    ),
    "derive_daily_actuals": ("weather_study_cli.application.actuals", "derive_daily_actuals"),
    "compute_accuracy_metrics": ("weather_study_cli.application.metrics", "compute_accuracy_metrics"),
    "compute_market_opportunity_metrics": (
        "weather_study_cli.application.market_metrics",
        "compute_market_opportunity_metrics",
    ),
    "build_study_report": ("weather_study_cli.application.pipeline", "build_study_report"),
    "ingest_capture_directory": ("weather_study_cli.application.ingest", "ingest_capture_directory"),
    "export_accuracy_html": ("weather_study_cli.application.report", "export_accuracy_html"),
    "generate_sample_capture_directory": (
        "weather_study_cli.application.sample_data",
        "generate_sample_capture_directory",
    ),
    "list_supported_study_places": ("weather_study_cli.application.cities", "list_supported_study_places"),
    "load_collection_gap_report": ("weather_study_cli.application.gaps", "load_collection_gap_report"),
    "load_capture_directory": ("weather_study_cli.application.raw_loader", "load_capture_directory"),
    "load_capture_file": ("weather_study_cli.application.raw_loader", "load_capture_file"),
    "load_day_drilldown_report": ("weather_study_cli.application.day_report", "load_day_drilldown_report"),
    "resolve_study_cities": ("weather_study_cli.application.cities", "resolve_study_cities"),
    "sync_capture_directory_from_s3": ("weather_study_cli.application.s3", "sync_capture_directory_from_s3"),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)
