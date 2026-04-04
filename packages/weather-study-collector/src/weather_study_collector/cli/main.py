from __future__ import annotations

import argparse
import json
import sys

from weather_study_cli.application import StudyValidationError, list_supported_study_places
from weather_study_collector.application import (
    DEFAULT_AWS_PROFILE,
    DEFAULT_CONTACT_EMAIL,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_S3_PREFIX,
    build_default_collector,
    parse_capture_time,
)


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve line breaks in examples."""


def build_parser() -> argparse.ArgumentParser:
    supported = "\n".join(f"  - {place}" for place in list_supported_study_places())
    parser = argparse.ArgumentParser(
        prog="weather-study-collector",
        description=(
            "Capture live raw city-hour study files using the existing weather and Kalshi adapters.\n\n"
            "Supported cities:\n"
            f"{supported}\n\n"
            "The collector validates every emitted payload against the weather-study raw contract\n"
            "before writing it to disk, and it persists one-side failures when the other source succeeds."
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser(
        "capture",
        help="Capture live weather-market study files to local disk.",
        description=(
            "Capture live weather-market study files to local disk.\n\n"
            "Examples:\n"
            "  weather-study-collector capture\n"
            "  weather-study-collector capture --place Seattle,WA --output-root /tmp/weather-study-live\n"
            "  weather-study-collector capture --captured-at-utc 2026-03-29T21:00:00Z --format json"
        ),
        formatter_class=HelpFormatter,
    )
    capture.add_argument(
        "--place",
        action="append",
        help='Optional strict city,state filter. Repeat to capture a subset, for example "Seattle,WA".',
    )
    capture.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory where study_version=... capture files will be written (default: %(default)s)",
    )
    capture.add_argument(
        "--captured-at-utc",
        help="Optional top-of-hour UTC timestamp to use for the capture, for example 2026-03-29T21:00:00Z",
    )
    capture.add_argument(
        "--contact-email",
        default=DEFAULT_CONTACT_EMAIL,
        help="Contact email embedded in the NOAA User-Agent header (default: %(default)s)",
    )
    capture.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the capture summary (default: %(default)s)",
    )

    capture_s3 = subparsers.add_parser(
        "capture-s3",
        help="Capture live weather-market study files and upload them to S3.",
        description=(
            "Capture live weather-market study files and upload them to S3.\n\n"
            "Examples:\n"
            "  weather-study-collector capture-s3 --bucket my-study-bucket\n"
            "  weather-study-collector capture-s3 --bucket my-study-bucket --place Seattle,WA\n"
            "  weather-study-collector capture-s3 --bucket my-study-bucket --prefix raw-live --format json"
        ),
        formatter_class=HelpFormatter,
    )
    capture_s3.add_argument(
        "--bucket",
        required=True,
        help="Target S3 bucket for raw study captures.",
    )
    capture_s3.add_argument(
        "--prefix",
        default=DEFAULT_S3_PREFIX,
        help="S3 prefix for uploaded raw files (default: %(default)s)",
    )
    capture_s3.add_argument(
        "--profile",
        default=DEFAULT_AWS_PROFILE,
        metavar="NAME",
        help=(
            "Optional AWS CLI named profile for S3 upload. When omitted, `aws` uses its default "
            "credential chain."
        ),
    )
    capture_s3.add_argument(
        "--place",
        action="append",
        help='Optional strict city,state filter. Repeat to capture a subset, for example "Seattle,WA".',
    )
    capture_s3.add_argument(
        "--captured-at-utc",
        help="Optional top-of-hour UTC timestamp to use for the capture, for example 2026-03-29T21:00:00Z",
    )
    capture_s3.add_argument(
        "--contact-email",
        default=DEFAULT_CONTACT_EMAIL,
        help="Contact email embedded in the NOAA User-Agent header (default: %(default)s)",
    )
    capture_s3.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the capture summary (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            collector = build_default_collector(contact_email=args.contact_email)
            summary = collector.capture_to_directory(
                output_root=args.output_root,
                places=args.place,
                captured_at_utc=parse_capture_time(args.captured_at_utc),
            )
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2))
            else:
                print(render_capture_summary(summary))
            return 0
        if args.command == "capture-s3":
            collector = build_default_collector(contact_email=args.contact_email)
            summary = collector.capture_to_s3(
                bucket=args.bucket,
                prefix=args.prefix,
                profile=args.profile,
                places=args.place,
                captured_at_utc=parse_capture_time(args.captured_at_utc),
            )
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2))
            else:
                print(render_s3_capture_summary(summary))
            return 0
    except StudyValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


def render_capture_summary(summary) -> str:
    lines = [
        f"Captured study files for {summary.target_count} city target(s) at {summary.captured_at_utc}",
        f"Output root: {summary.output_root}",
        f"written: {summary.written_count}",
        f"success: {summary.success_count}",
        f"partial: {summary.partial_count}",
        f"failed: {summary.failed_count}",
        "",
        "Results:",
    ]
    for result in summary.results:
        lines.append(f"  {result.place}: {result.status}")
        if result.path:
            lines.append(f"    file: {result.path}")
        for source, message in zip(result.error_sources, result.error_messages, strict=False):
            lines.append(f"    {source}: {message}")
    return "\n".join(lines)


def render_s3_capture_summary(summary) -> str:
    profile_line = (
        "AWS profile: (default credential chain)"
        if summary.profile is None or not str(summary.profile).strip()
        else f"AWS profile: {summary.profile.strip()}"
    )
    lines = [
        f"Uploaded study captures for {summary.target_count} city target(s) at {summary.captured_at_utc}",
        f"S3 prefix: s3://{summary.bucket}/{summary.prefix}/" if summary.prefix else f"S3 bucket: s3://{summary.bucket}/",
        profile_line,
        f"uploaded: {summary.uploaded_count}",
        f"success: {summary.success_count}",
        f"partial: {summary.partial_count}",
        f"failed: {summary.failed_count}",
        "",
        "Results:",
    ]
    for result in summary.results:
        lines.append(f"  {result.place}: {result.status}")
        if result.s3_uri:
            lines.append(f"    s3: {result.s3_uri}")
        for source, message in zip(result.error_sources, result.error_messages, strict=False):
            lines.append(f"    {source}: {message}")
    return "\n".join(lines)
