from __future__ import annotations

import argparse
import json
import sys

from weather_study_cli.application import DEFAULT_MOCK_DATA_DIR, WeatherStudyCliError, load_capture_directory


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = load_capture_directory(args.input)
    except WeatherStudyCliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=False))
    else:
        print(render_text_summary(summary))
    return 0


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
