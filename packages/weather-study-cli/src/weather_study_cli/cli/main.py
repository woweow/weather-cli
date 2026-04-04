from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from weather_study_cli.application import (
    AccuracyMetricSummary,
    BuildStudyReportSummary,
    CollectionGapReport,
    ValidStudyDaysSummary,
    DEFAULT_AWS_PROFILE,
    DEFAULT_DB_PATH,
    DEFAULT_HTML_REPORT_PATH,
    DEFAULT_MOCK_DATA_DIR,
    DEFAULT_CONTACT_EMAIL,
    DEFAULT_S3_DOWNLOAD_DIR,
    DEFAULT_S3_PREFIX,
    DEFAULT_SAMPLE_DAY_COUNT,
    DEFAULT_SAMPLE_METADATA_PATH,
    DEFAULT_SAMPLE_OUTPUT_ROOT,
    DEFAULT_SAMPLE_PLACES,
    DEFAULT_SAMPLE_S3_PREFIX,
    MarketOpportunityMetricSummary,
    build_study_report,
    StudyDayDrilldownReport,
    WeatherStudyCliError,
    compute_accuracy_metrics,
    compute_market_opportunity_metrics,
    count_valid_study_days,
    derive_daily_actuals,
    export_accuracy_html,
    generate_sample_capture_directory,
    ingest_capture_directory,
    load_capture_directory,
    load_collection_gap_report,
    load_day_drilldown_report,
    sync_capture_directory_from_s3,
)


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve line breaks in examples."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather-study",
        description=(
            "Validate local raw city-hour study captures for the forecast-confidence PRD.\n\n"
            "The loader expects S3-style paths such as:\n"
            "  study_version=1/city=Seattle/state=WA/local_date=2026-03-26/\n"
            "  local_hour=09/captured_at_utc=2026-03-26T16-00-00Z.json\n\n"
            "Use the same code path for the bundled mock dataset and future S3 downloads\n"
            "copied to local disk."
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate-raw",
        help="Validate raw capture files from a directory or single file.",
        description=(
            "Validate raw capture files from a directory or a single file.\n\n"
            "Examples:\n"
            "  weather-study validate-raw\n"
            "  weather-study validate-raw --input packages/weather-study-cli/mock-data/raw\n"
            "  weather-study validate-raw --format json"
        ),
        formatter_class=HelpFormatter,
    )
    validate.add_argument(
        "--input",
        default=str(DEFAULT_MOCK_DATA_DIR),
        help="Root directory or single file to validate (default: %(default)s)",
    )
    validate.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the validation summary (default: %(default)s)",
    )

    sync_s3 = subparsers.add_parser(
        "sync-s3",
        help="Sync raw study captures from S3 to local disk.",
        description=(
            "Sync raw study captures from S3 to local disk using the AWS CLI.\n\n"
            "Examples:\n"
            "  weather-study sync-s3 --bucket my-study-bucket\n"
            "  weather-study sync-s3 --bucket my-study-bucket --output-root /tmp/weather-study-s3\n"
            "  weather-study sync-s3 --bucket my-study-bucket --prefix raw --profile dev --delete"
        ),
        formatter_class=HelpFormatter,
    )
    sync_s3.add_argument(
        "--bucket",
        required=True,
        help="S3 bucket containing raw study captures.",
    )
    sync_s3.add_argument(
        "--prefix",
        default=DEFAULT_S3_PREFIX,
        help="S3 prefix under the bucket to sync from (default: %(default)s)",
    )
    sync_s3.add_argument(
        "--output-root",
        default=str(DEFAULT_S3_DOWNLOAD_DIR),
        help="Local root directory where synced raw files will be written (default: %(default)s)",
    )
    sync_s3.add_argument(
        "--profile",
        default=DEFAULT_AWS_PROFILE,
        help=(
            'AWS CLI profile for sync; pass "" to use the default credential chain '
            "(env vars, instance role) without --profile (default: %(default)s)"
        ),
    )
    sync_s3.add_argument(
        "--delete",
        action="store_true",
        help="Delete local files that no longer exist under the S3 prefix.",
    )
    sync_s3.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview sync actions without downloading files.",
    )
    sync_s3.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip raw-contract validation after sync.",
    )
    sync_s3.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the sync summary (default: %(default)s)",
    )

    ingest = subparsers.add_parser(
        "ingest-raw",
        help="Ingest raw capture files into the local study SQLite database.",
        description=(
            "Ingest raw capture files into the local study SQLite database.\n\n"
            "The command creates the dedicated study schema if needed, upserts raw captures by\n"
            "stable city/date/hour/captured-at key, and replaces normalized forecast/market rows\n"
            "for any capture it reprocesses.\n\n"
            "Examples:\n"
            "  weather-study ingest-raw\n"
            "  weather-study ingest-raw --reset\n"
            "  weather-study ingest-raw --db-path /tmp/weather-study.db --format json"
        ),
        formatter_class=HelpFormatter,
    )
    ingest.add_argument(
        "--input",
        default=str(DEFAULT_MOCK_DATA_DIR),
        help="Root directory or single file to ingest (default: %(default)s)",
    )
    ingest.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study ingest (default: %(default)s)",
    )
    ingest.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing study DB first and rebuild it from the supplied raw files.",
    )
    ingest.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the ingest summary (default: %(default)s)",
    )

    derive = subparsers.add_parser(
        "derive-daily-actuals",
        help="Fetch NOAA observed highs for completed local dates in the study DB.",
        description=(
            "Fetch NOAA observed highs for completed local dates already present in the study DB.\n\n"
            "The command reads distinct place/date targets from `raw_captures`, skips any date that\n"
            "has not completed yet in that city's timezone, and upserts results into `daily_actuals`.\n\n"
            "Examples:\n"
            "  weather-study derive-daily-actuals\n"
            "  weather-study derive-daily-actuals --db-path /tmp/weather-study.db --format json\n"
            "  weather-study derive-daily-actuals --place Seattle,WA --local-date 2026-03-26"
        ),
        formatter_class=HelpFormatter,
    )
    derive.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study DB (default: %(default)s)",
    )
    derive.add_argument(
        "--place",
        help='Optional strict city,state filter such as "Seattle,WA".',
    )
    derive.add_argument(
        "--local-date",
        help="Optional YYYY-MM-DD filter for a single local date.",
    )
    derive.add_argument(
        "--contact-email",
        default=DEFAULT_CONTACT_EMAIL,
        help="Contact email embedded in the NOAA User-Agent header (default: %(default)s)",
    )
    derive.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the derivation summary (default: %(default)s)",
    )

    metrics = subparsers.add_parser(
        "compute-accuracy-metrics",
        help="Compute hourly forecast-confidence metrics from the study DB.",
        description=(
            "Compute hourly forecast-confidence metrics from ingested captures and daily actuals.\n\n"
            "The command compares each city-day capture hour's remaining-day forecast high against\n"
            "the derived final observed high for that local date, then writes aggregated rows into\n"
            "`hourly_accuracy_metrics`.\n\n"
            "Examples:\n"
            "  weather-study compute-accuracy-metrics\n"
            "  weather-study compute-accuracy-metrics --db-path /tmp/weather-study.db --format json\n"
            "  weather-study compute-accuracy-metrics --place Seattle,WA"
        ),
        formatter_class=HelpFormatter,
    )
    metrics.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study DB (default: %(default)s)",
    )
    metrics.add_argument(
        "--place",
        help='Optional strict city,state filter such as "Seattle,WA".',
    )
    metrics.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the metric summary (default: %(default)s)",
    )

    market_metrics = subparsers.add_parser(
        "compute-market-opportunity-metrics",
        help="Compute hourly market-opportunity metrics from the study DB.",
        description=(
            "Compute hourly market-opportunity metrics from ingested captures and daily actuals.\n\n"
            "The command resolves the actual winning Kalshi bucket for each city-day when possible,\n"
            "tracks whether the market leader already matched that winning bucket at each hour, and\n"
            "stores the aggregated results in `hourly_market_opportunity_metrics`.\n\n"
            "Examples:\n"
            "  weather-study compute-market-opportunity-metrics\n"
            "  weather-study compute-market-opportunity-metrics --db-path /tmp/weather-study.db --format json\n"
            "  weather-study compute-market-opportunity-metrics --place Seattle,WA"
        ),
        formatter_class=HelpFormatter,
    )
    market_metrics.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study DB (default: %(default)s)",
    )
    market_metrics.add_argument(
        "--place",
        help='Optional strict city,state filter such as "Seattle,WA".',
    )
    market_metrics.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the metric summary (default: %(default)s)",
    )

    export = subparsers.add_parser(
        "export-accuracy-html",
        help="Export a self-contained local HTML view of hourly forecast accuracy.",
        description=(
            "Export a self-contained local HTML view of hourly forecast accuracy.\n\n"
            "The document reads from already-computed `hourly_accuracy_metrics` rows and renders\n"
            "one city chart per place. Each chart shows hourly forecast accuracy on the y-axis and\n"
            "the representative winning market label plus its average price beneath each hour.\n\n"
            "Examples:\n"
            "  weather-study export-accuracy-html --output /tmp/weather-study.html\n"
            "  weather-study export-accuracy-html --db-path /tmp/weather-study.db --place Seattle,WA\n"
            "  weather-study export-accuracy-html --min-valid-sample 5 > accuracy.html"
        ),
        formatter_class=HelpFormatter,
    )
    export.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study DB (default: %(default)s)",
    )
    export.add_argument(
        "--output",
        help="Path to write the HTML file. Omit to print HTML to stdout.",
    )
    export.add_argument(
        "--place",
        help='Optional strict city,state filter such as "Seattle,WA".',
    )
    export.add_argument(
        "--min-valid-sample",
        type=int,
        default=5,
        help="Threshold below which the UI shows a thin-sample warning (default: %(default)s)",
    )

    sample = subparsers.add_parser(
        "generate-sample-data",
        help="Generate a week of hourly Seattle/Denver study captures for UI demos.",
        description=(
            "Generate a synthetic week of hourly raw study captures for UI/report demos.\n\n"
            "The command fetches NOAA observed highs for the requested completed local dates, then\n"
            "builds synthetic remaining-day forecasts and Kalshi-style ladders that intentionally\n"
            "converge on the observed winner through the day. By default it writes Seattle and Denver\n"
            "sample captures to the bundled mock-data directory used by `weather-study build-report`.\n\n"
            "Examples:\n"
            "  weather-study generate-sample-data\n"
            "  weather-study generate-sample-data --output-root /tmp/weather-study-sample --day-count 7\n"
            "  weather-study generate-sample-data --bucket weather-study-raw-084375548651-us-west-2 \\\n"
            "    --prefix sample/weather-study-weekly-2026-03-29 --format json"
        ),
        formatter_class=HelpFormatter,
    )
    sample.add_argument(
        "--place",
        action="append",
        help=(
            "Optional city,state selector. Repeat to override the default sample cities "
            f"({', '.join(DEFAULT_SAMPLE_PLACES)})."
        ),
    )
    sample.add_argument(
        "--output-root",
        default=str(DEFAULT_SAMPLE_OUTPUT_ROOT),
        help="Root directory where generated raw files will be written (default: %(default)s)",
    )
    sample.add_argument(
        "--metadata-path",
        default=str(DEFAULT_SAMPLE_METADATA_PATH),
        help="Path for the generated metadata manifest (default: %(default)s)",
    )
    sample.add_argument(
        "--day-count",
        type=int,
        default=DEFAULT_SAMPLE_DAY_COUNT,
        help="Number of completed local dates to generate per city (default: %(default)s)",
    )
    sample.add_argument(
        "--end-local-date",
        help="Optional inclusive YYYY-MM-DD end date. Defaults to yesterday in the sampled cities.",
    )
    sample.add_argument(
        "--bucket",
        help="Optional S3 bucket to upload the generated raw files to after local generation.",
    )
    sample.add_argument(
        "--prefix",
        default=DEFAULT_SAMPLE_S3_PREFIX,
        help="S3 prefix to upload to when --bucket is supplied (default: %(default)s)",
    )
    sample.add_argument(
        "--profile",
        default=DEFAULT_AWS_PROFILE,
        help=(
            'AWS CLI profile for optional upload; pass "" for the default credential chain '
            "(default: %(default)s)"
        ),
    )
    sample.add_argument(
        "--contact-email",
        default=DEFAULT_CONTACT_EMAIL,
        help="Contact email embedded in the NOAA User-Agent header (default: %(default)s)",
    )
    sample.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the generation summary (default: %(default)s)",
    )

    build_report = subparsers.add_parser(
        "build-report",
        help="Sync, ingest, derive, compute, and export the local study report in one pass.",
        description=(
            "Run the full local study-report build pipeline in one pass.\n\n"
            "The command optionally syncs raw captures from S3, resets the study DB from those raw\n"
            "files, derives completed daily actual highs, recomputes both metric tables, and writes\n"
            "the self-contained HTML export.\n\n"
            "Examples:\n"
            "  weather-study build-report\n"
            "  weather-study build-report --output /tmp/weather-study.html --db-path /tmp/weather-study.db\n"
            "  weather-study build-report --bucket my-study-bucket --prefix raw-mock-seed --output /tmp/weather-study.html"
        ),
        formatter_class=HelpFormatter,
    )
    build_report.add_argument(
        "--input",
        default=str(DEFAULT_MOCK_DATA_DIR),
        help="Local raw root to build from when --bucket is not supplied (default: %(default)s)",
    )
    build_report.add_argument(
        "--bucket",
        help="Optional S3 bucket to sync from before rebuilding the local study DB.",
    )
    build_report.add_argument(
        "--prefix",
        default=DEFAULT_S3_PREFIX,
        help="S3 prefix to sync from when --bucket is supplied (default: %(default)s)",
    )
    build_report.add_argument(
        "--sync-output-root",
        default=str(DEFAULT_S3_DOWNLOAD_DIR),
        help="Local root directory for synced S3 raw files (default: %(default)s)",
    )
    build_report.add_argument(
        "--profile",
        default=DEFAULT_AWS_PROFILE,
        help=(
            'AWS CLI profile when syncing from S3; pass "" for the default credential chain '
            "(default: %(default)s)"
        ),
    )
    build_report.add_argument(
        "--delete",
        action="store_true",
        help="Delete local synced raw files that no longer exist under the S3 prefix.",
    )
    build_report.add_argument(
        "--skip-sync-validate",
        action="store_true",
        help="Skip raw-contract validation after S3 sync.",
    )
    build_report.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study DB (default: %(default)s)",
    )
    build_report.add_argument(
        "--output",
        default=str(DEFAULT_HTML_REPORT_PATH),
        help="Path to write the HTML report (default: %(default)s)",
    )
    build_report.add_argument(
        "--place",
        help='Optional strict city,state filter such as "Seattle,WA" for actuals, metrics, and export.',
    )
    build_report.add_argument(
        "--contact-email",
        default=DEFAULT_CONTACT_EMAIL,
        help="Contact email embedded in the NOAA User-Agent header (default: %(default)s)",
    )
    build_report.add_argument(
        "--min-valid-sample",
        type=int,
        default=5,
        help="Threshold below which the UI shows a thin-sample warning (default: %(default)s)",
    )
    build_report.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the build summary (default: %(default)s)",
    )

    gaps = subparsers.add_parser(
        "report-gaps",
        help="Report missing city-hours from ingested raw captures.",
        description=(
            "Report missing city-hours from the local study SQLite database.\n\n"
            "The command derives per-city, per-date expected hourly coverage from `raw_captures`,\n"
            "treats completed dates as full 24-hour windows, and treats the current local date as\n"
            "expected only through the current local hour.\n\n"
            "Examples:\n"
            "  weather-study report-gaps\n"
            "  weather-study report-gaps --db-path /tmp/weather-study.db --format json\n"
            "  weather-study report-gaps --place Seattle,WA"
        ),
        formatter_class=HelpFormatter,
    )
    gaps.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study DB (default: %(default)s)",
    )
    gaps.add_argument(
        "--place",
        help='Optional strict city,state filter such as "Seattle,WA".',
    )
    gaps.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the gap report (default: %(default)s)",
    )

    valid_days = subparsers.add_parser(
        "count-valid-study-days",
        help="List supported cities with complete local-day capture counts.",
        description=(
            "For each configured study city, count local dates with no missing expected city-hours.\n\n"
            "Uses the same expected-hour window as `report-gaps` (full 0–23 for completed dates;\n"
            "partial window for the current local date). Does not apply chart-spec eligibility.\n\n"
            "Examples:\n"
            "  weather-study count-valid-study-days\n"
            "  weather-study count-valid-study-days --db-path /tmp/weather-study.db --format json"
        ),
        formatter_class=HelpFormatter,
    )
    valid_days.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study DB (default: %(default)s)",
    )
    valid_days.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: %(default)s)",
    )

    drilldown = subparsers.add_parser(
        "export-day-drilldown",
        help="Export a single city-day drill-down from the study DB.",
        description=(
            "Export a single city-day drill-down from the local study SQLite database.\n\n"
            "The report shows each captured hour for one city-day, including remaining-day forecast\n"
            "periods, captured market ladders, raw error sources, and whether each forecast high\n"
            "matched the resolved observed high when one exists.\n\n"
            "Examples:\n"
            "  weather-study export-day-drilldown --place Seattle,WA --local-date 2026-03-26\n"
            "  weather-study export-day-drilldown --place Denver,CO --local-date 2026-03-27 --format json\n"
            "  weather-study export-day-drilldown --place Seattle,WA --local-date 2026-03-26 --output /tmp/day.json --format json"
        ),
        formatter_class=HelpFormatter,
    )
    drilldown.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path for the study DB (default: %(default)s)",
    )
    drilldown.add_argument(
        "--place",
        required=True,
        help='Strict city,state selector such as "Seattle,WA".',
    )
    drilldown.add_argument(
        "--local-date",
        required=True,
        help="Target local date in YYYY-MM-DD format.",
    )
    drilldown.add_argument(
        "--output",
        help="Optional path to write the exported drill-down instead of printing to stdout.",
    )
    drilldown.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the drill-down export (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-raw":
            summary = load_capture_directory(args.input)
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_text_summary(summary))
            return 0
        if args.command == "sync-s3":
            summary = sync_capture_directory_from_s3(
                args.bucket,
                prefix=args.prefix,
                output_root=args.output_root,
                profile=args.profile,
                delete=args.delete,
                dry_run=args.dry_run,
                validate=not args.skip_validate,
            )
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_s3_sync_text_summary(summary))
            return 0
        if args.command == "ingest-raw":
            summary = ingest_capture_directory(args.input, db_path=args.db_path, reset=args.reset)
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_ingest_text_summary(summary))
            return 0
        if args.command == "derive-daily-actuals":
            summary = derive_daily_actuals(
                db_path=args.db_path,
                place=args.place,
                local_date=args.local_date,
                contact_email=args.contact_email,
            )
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_actuals_text_summary(summary))
            return 0
        if args.command == "compute-accuracy-metrics":
            summary = compute_accuracy_metrics(db_path=args.db_path, place=args.place)
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_accuracy_text_summary(summary))
            return 0
        if args.command == "compute-market-opportunity-metrics":
            summary = compute_market_opportunity_metrics(db_path=args.db_path, place=args.place)
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_market_opportunity_text_summary(summary))
            return 0
        if args.command == "export-accuracy-html":
            return export_accuracy_html(
                db_path=args.db_path,
                output_path=args.output,
                place=args.place,
                min_valid_sample=args.min_valid_sample,
            )
        if args.command == "generate-sample-data":
            summary = generate_sample_capture_directory(
                output_root=args.output_root,
                metadata_path=args.metadata_path,
                places=args.place,
                day_count=args.day_count,
                end_local_date=args.end_local_date,
                bucket=args.bucket,
                prefix=args.prefix,
                profile=args.profile,
                contact_email=args.contact_email,
            )
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_sample_generation_text_summary(summary))
            return 0
        if args.command == "build-report":
            summary = build_study_report(
                input_path=args.input,
                db_path=args.db_path,
                output_path=args.output,
                place=args.place,
                min_valid_sample=args.min_valid_sample,
                bucket=args.bucket,
                prefix=args.prefix,
                sync_output_root=args.sync_output_root,
                profile=args.profile,
                delete=args.delete,
                validate_sync=not args.skip_sync_validate,
                contact_email=args.contact_email,
            )
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_build_report_text_summary(summary))
            return 0
        if args.command == "report-gaps":
            summary = load_collection_gap_report(db_path=args.db_path, place=args.place)
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_gap_text_summary(summary))
            return 0
        if args.command == "count-valid-study-days":
            summary = count_valid_study_days(db_path=args.db_path)
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
            else:
                print(render_valid_study_days_text_summary(summary))
            return 0
        if args.command == "export-day-drilldown":
            summary = load_day_drilldown_report(
                db_path=args.db_path,
                place=args.place,
                local_date=args.local_date,
            )
            output = (
                json.dumps(summary.to_dict(), indent=2, sort_keys=False)
                if args.format == "json"
                else render_day_drilldown_text_summary(summary)
            )
            if args.output:
                target = Path(args.output).expanduser().resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(output + ("\n" if not output.endswith("\n") else ""), encoding="utf-8")
            else:
                print(output)
            return 0
    except WeatherStudyCliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


def render_text_summary(summary) -> str:
    lines = [
        f"Validated {summary.file_count} raw capture files from {summary.root}",
        f"Cities: {', '.join(summary.cities)}",
        f"Dates: {', '.join(summary.local_dates)}",
        f"Partial failures: weather missing {summary.weather_missing_count}, market missing {summary.market_missing_count}",
        "",
        "Capture windows:",
    ]
    for window in summary.capture_windows:
        lines.append(
            f"  {window['city']} {window['local_date']}: hours {', '.join(f'{hour:02d}' for hour in window['hours'])}"
        )
        if window["missing_weather_hours"]:
            lines.append(
                "    weather missing at "
                + ", ".join(f"{hour:02d}" for hour in window["missing_weather_hours"])
            )
        if window["missing_market_hours"]:
            lines.append(
                "    market missing at "
                + ", ".join(f"{hour:02d}" for hour in window["missing_market_hours"])
            )
    return "\n".join(lines)


def render_s3_sync_text_summary(summary) -> str:
    lines = [
        f"Synced raw study files from {summary.source_uri} to {summary.output_root}",
        f"AWS profile: {summary.profile}",
        f"dry run: {'yes' if summary.dry_run else 'no'}",
        f"delete: {'yes' if summary.delete else 'no'}",
    ]
    if summary.validation is not None:
        lines.extend(["", render_text_summary(summary.validation)])
    elif summary.aws_output_lines:
        lines.extend(["", "AWS CLI output:"])
        lines.extend(f"  {line}" for line in summary.aws_output_lines)
    return "\n".join(lines)


def render_ingest_text_summary(summary) -> str:
    lines = [
        f"Ingested {summary.ingested_capture_count} raw capture files from {summary.input_root}",
        f"SQLite database: {summary.db_path}",
        f"raw_captures: {summary.raw_capture_count}",
        f"forecast_periods: {summary.forecast_period_count}",
        f"market_rows: {summary.market_row_count}",
        f"daily_actuals: {summary.daily_actual_count}",
        f"hourly_accuracy_metrics: {summary.hourly_accuracy_metric_count}",
        f"hourly_market_opportunity_metrics: {summary.hourly_market_opportunity_metric_count}",
    ]
    return "\n".join(lines)


def render_actuals_text_summary(summary) -> str:
    lines = [
        f"SQLite database: {summary.db_path}",
        f"target city-days: {summary.target_count}",
        f"resolved daily actuals: {summary.resolved_count}",
        f"skipped incomplete local dates: {summary.skipped_incomplete_count}",
        f"daily_actuals rows: {summary.daily_actual_count}",
    ]
    return "\n".join(lines)


def render_accuracy_text_summary(summary: AccuracyMetricSummary) -> str:
    lines = [
        f"SQLite database: {summary.db_path}",
        f"places with metrics: {summary.place_count}",
        f"hourly_accuracy_metrics rows: {summary.metric_row_count}",
    ]
    return "\n".join(lines)


def render_market_opportunity_text_summary(summary: MarketOpportunityMetricSummary) -> str:
    lines = [
        f"SQLite database: {summary.db_path}",
        f"places with market metrics: {summary.place_count}",
        f"hourly_market_opportunity_metrics rows: {summary.metric_row_count}",
    ]
    return "\n".join(lines)


def render_sample_generation_text_summary(summary) -> str:
    window = (
        "n/a"
        if not summary.local_dates
        else summary.local_dates[0]
        if len(summary.local_dates) == 1
        else f"{summary.local_dates[0]} -> {summary.local_dates[-1]}"
    )
    lines = [
        f"Generated {summary.capture_count} sample raw captures",
        f"Output root: {summary.output_root}",
        f"Metadata manifest: {summary.metadata_path}",
        f"Places: {', '.join(summary.places)}",
        f"Local date window: {window}",
    ]
    if summary.bucket is not None:
        prefix = "" if summary.prefix is None else summary.prefix
        lines.extend(
            [
                f"S3 target: s3://{summary.bucket}/{prefix}/" if prefix else f"S3 target: s3://{summary.bucket}/",
                f"AWS profile: {summary.profile}",
            ]
        )
    return "\n".join(lines)


def render_valid_study_days_text_summary(summary: ValidStudyDaysSummary) -> str:
    lines = [
        f"SQLite database: {summary.db_path}",
        f"generated_at_utc: {summary.generated_at_utc}",
        "",
        "Valid complete local days (no missing expected hours, same rules as report-gaps):",
    ]
    for row in summary.places:
        label = row.city if row.has_captures else f"{row.city} (no captures)"
        lines.append(f"  {label}: {row.valid_day_count}")
    return "\n".join(lines)


def render_gap_text_summary(summary: CollectionGapReport) -> str:
    lines = [
        f"SQLite database: {summary.db_path}",
        f"configured study cities: {summary.configured_place_count}",
        f"places in gap report: {summary.place_count}",
        f"date windows inspected: {summary.date_count}",
        f"expected city-hours: {summary.expected_hour_count}",
        f"observed city-hours: {summary.observed_hour_count}",
        f"missing city-hours: {summary.missing_hour_count}",
        f"dates with gaps: {summary.gap_date_count}",
        f"coverage ratio: {summary.coverage_ratio:.1%}",
    ]
    if summary.missing_supported_places:
        lines.append(
            "supported cities without captures: " + ", ".join(summary.missing_supported_places)
        )
    for place in summary.places:
        lines.extend(
            [
                "",
                (
                    f"{place.place}: {place.observed_hour_count}/{place.expected_hour_count} expected hours present "
                    f"({place.coverage_ratio:.1%} coverage)"
                ),
            ]
        )
        gap_dates = [date for date in place.dates if date.missing_hour_count > 0]
        if not gap_dates:
            lines.append("  no missing hours")
            continue
        for date in gap_dates:
            current_suffix = " (in progress)" if date.is_current_local_date else ""
            missing_hours = ", ".join(f"{hour:02d}" for hour in date.missing_hours)
            observed_hours = ", ".join(f"{hour:02d}" for hour in date.observed_hours) or "none"
            lines.append(
                (
                    f"  {date.local_date}{current_suffix}: window {date.expected_start_hour:02d}-"
                    f"{date.expected_end_hour:02d}, observed {observed_hours}, missing {missing_hours}"
                )
            )
    return "\n".join(lines)


def render_build_report_text_summary(summary: BuildStudyReportSummary) -> str:
    lines = [
        f"Built study report from {summary.input_root}",
        f"SQLite database: {summary.db_path}",
        f"HTML report: {summary.output_path}",
    ]
    if summary.sync is not None:
        lines.extend(
            [
                f"S3 source: {summary.sync.source_uri}",
                f"AWS profile: {summary.sync.profile}",
            ]
        )
    lines.extend(
        [
            f"raw_captures: {summary.ingest.raw_capture_count}",
            f"forecast_periods: {summary.ingest.forecast_period_count}",
            f"market_rows: {summary.ingest.market_row_count}",
            f"daily_actuals: {summary.actuals.daily_actual_count}",
            f"hourly_accuracy_metrics: {summary.accuracy_metrics.metric_row_count}",
            f"hourly_market_opportunity_metrics: {summary.market_metrics.metric_row_count}",
            f"skipped incomplete local dates: {summary.actuals.skipped_incomplete_count}",
            f"configured study cities: {summary.gaps.configured_place_count}",
            f"places in gap report: {summary.gaps.place_count}",
            (
                "supported cities without captures: none"
                if not summary.gaps.missing_supported_places
                else "supported cities without captures: "
                + ", ".join(summary.gaps.missing_supported_places)
            ),
        ]
    )
    if summary.cities:
        lines.append("city maturity:")
        for city in summary.cities:
            window = (
                "n/a"
                if city.capture_window_start_date is None and city.capture_window_end_date is None
                else city.capture_window_start_date
                if city.capture_window_start_date == city.capture_window_end_date
                or city.capture_window_end_date is None
                else f"{city.capture_window_start_date} -> {city.capture_window_end_date}"
            )
            lines.append(
                (
                    f"  {city.place}: {city.resolved_actual_day_count}/{city.capture_day_count} resolved days, "
                    f"window {window}"
                )
            )
    return "\n".join(lines)


def render_day_drilldown_text_summary(summary: StudyDayDrilldownReport) -> str:
    actual = (
        f"{summary.actual_high_temperature_f:.1f} F at {summary.actual_resolved_at_utc}"
        if summary.actual_high_temperature_f is not None and summary.actual_resolved_at_utc is not None
        else "unresolved"
    )
    lines = [
        f"SQLite database: {summary.db_path}",
        f"Day drill-down: {summary.place} on {summary.local_date}",
        f"Timezone: {summary.timezone}",
        f"Actual high: {actual}",
        f"captures: {summary.capture_count}",
        f"forecast matches actual: {summary.correct_capture_count}",
    ]
    for capture in summary.captures:
        forecast_high = (
            f"{capture.forecast_high_temperature_f:.1f} F"
            if capture.forecast_high_temperature_f is not None
            else "n/a"
        )
        if capture.forecast_matches_actual is None:
            forecast_match = "unresolved"
        else:
            forecast_match = "yes" if capture.forecast_matches_actual else "no"
        market_leader = (
            f"{capture.market_leader_label} @ {capture.market_leader_last_price_cents}c"
            if capture.market_leader_label is not None and capture.market_leader_last_price_cents is not None
            else "n/a"
        )
        lines.extend(
            [
                "",
                (
                    f"{capture.local_hour:02d}:00 local | forecast high {forecast_high} | "
                    f"matches actual {forecast_match} | market leader {market_leader}"
                ),
                (
                    f"  weather payload: {'yes' if capture.weather_payload_present else 'no'} "
                    f"({capture.forecast_period_count} periods), market payload: "
                    f"{'yes' if capture.market_payload_present else 'no'} ({capture.market_row_count} rows)"
                ),
            ]
        )
        if capture.error_sources:
            lines.append(
                "  errors: "
                + "; ".join(
                    f"{source}: {message}"
                    for source, message in zip(capture.error_sources, capture.error_messages, strict=True)
                )
            )
    return "\n".join(lines)
