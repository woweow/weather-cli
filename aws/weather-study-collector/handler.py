from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3

from weather_study_collector.application import DEFAULT_CONTACT_EMAIL, build_default_collector, parse_capture_time


DEFAULT_PREFIX = "raw"
DEFAULT_COLLECTOR_NAME = "weather-market-study-lambda"


def handler(event, context):
    payload = event or {}
    bucket = _required_bucket(payload)
    prefix = str(payload.get("prefix") or os.getenv("WEATHER_STUDY_PREFIX", DEFAULT_PREFIX)).strip().strip("/")
    places = payload.get("places")
    contact_email = os.getenv("WEATHER_STUDY_CONTACT_EMAIL", DEFAULT_CONTACT_EMAIL)
    collector_name = os.getenv("WEATHER_STUDY_COLLECTOR_NAME", DEFAULT_COLLECTOR_NAME)
    captured_at_utc = parse_capture_time(payload.get("captured_at_utc"))

    collector = build_default_collector(
        contact_email=contact_email,
        collector_name=collector_name,
    )
    s3_client = boto3.client("s3")

    with TemporaryDirectory(prefix="weather-study-lambda-") as temp_dir:
        temp_root = Path(temp_dir).resolve()
        summary = collector.capture_to_directory(
            output_root=temp_root,
            places=places,
            captured_at_utc=captured_at_utc,
        )
        upload_results = []
        uploaded_uris = []
        for result in summary.results:
            s3_uri = None
            if result.path is not None:
                relative_path = Path(result.path).relative_to(temp_root)
                key = "/".join(([prefix] if prefix else []) + list(relative_path.parts))
                s3_client.upload_file(
                    result.path,
                    bucket,
                    key,
                    ExtraArgs={"ContentType": "application/json"},
                )
                s3_uri = f"s3://{bucket}/{key}"
                uploaded_uris.append(s3_uri)
            upload_results.append(
                {
                    "place": result.place,
                    "status": result.status,
                    "s3_uri": s3_uri,
                    "error_sources": list(result.error_sources),
                    "error_messages": list(result.error_messages),
                }
            )

    return {
        "captured_at_utc": summary.captured_at_utc,
        "bucket": bucket,
        "prefix": prefix,
        "target_count": summary.target_count,
        "uploaded_count": len(uploaded_uris),
        "success_count": summary.success_count,
        "partial_count": summary.partial_count,
        "failed_count": summary.failed_count,
        "uploaded_uris": uploaded_uris,
        "results": upload_results,
    }


def _required_bucket(payload: dict) -> str:
    bucket = str(payload.get("bucket") or os.getenv("WEATHER_STUDY_BUCKET", "")).strip()
    if not bucket:
        raise ValueError("WEATHER_STUDY_BUCKET or event.bucket is required.")
    return bucket
