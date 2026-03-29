from __future__ import annotations

import argparse
import json
import sys

from weather_study_cli.application import (
    AccuracyMetricSummary,
    DEFAULT_DB_PATH,
    DEFAULT_MOCK_DATA_DIR,
    DEFAULT_CONTACT_EMAIL,
    WeatherStudyCliError,
    compute_accuracy_metrics,
    derive_daily_actuals,
    export_accuracy_html,
    ingest_capture_directory,
    load_capture_directory,
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

    export = subparsers.add_parser(
        "export-accuracy-html",
        help="Export a self-contained local HTML view of hourly forecast accuracy.",
        description=(
            "Export a self-contained local HTML view of hourly forecast accuracy.\n\n"
            "The document reads from already-computed `hourly_accuracy_metrics` rows and renders\n"
            "a city selector, hourly accuracy chart, coverage cards, and thin-sample warning.\n\n"
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
        if args.command == "export-accuracy-html":
            return export_accuracy_html(
                db_path=args.db_path,
                output_path=args.output,
                place=args.place,
                min_valid_sample=args.min_valid_sample,
            )
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
