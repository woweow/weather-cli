from __future__ import annotations

import json
import os
import subprocess
from tempfile import TemporaryDirectory
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from kalshi_weather_markets_cli.adapters.client import KalshiPublicClient
from kalshi_weather_markets_cli.application.service import KalshiWeatherService
from weather_cli.adapters.geocoding import OpenMeteoGeocoder
from weather_cli.adapters.http import JsonHttpClient
from weather_cli.adapters.noaa import NoaaApi
from weather_cli.application.service import WeatherService
from weather_study_cli.application.cities import resolve_study_cities
from weather_study_cli.application.errors import StudyValidationError
from weather_study_cli.application.raw_loader import build_capture_relative_path
from weather_study_cli.application.raw_schema import StudyCapture


DEFAULT_OUTPUT_ROOT = Path(".study") / "raw"
DEFAULT_CONTACT_EMAIL = os.getenv("WEATHER_CLI_CONTACT_EMAIL", "weather-cli@example.com")
DEFAULT_COLLECTOR_NAME = "weather-market-study-local"
DEFAULT_COLLECTOR_VERSION = "1"
DEFAULT_AWS_PROFILE = "dev"
DEFAULT_S3_PREFIX = "raw"
SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class CaptureWriteResult:
    place: str
    status: str
    path: str | None
    error_sources: tuple[str, ...]
    error_messages: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "place": self.place,
            "status": self.status,
            "path": self.path,
            "error_sources": list(self.error_sources),
            "error_messages": list(self.error_messages),
        }


@dataclass(frozen=True)
class CollectorRunSummary:
    captured_at_utc: str
    output_root: Path
    results: tuple[CaptureWriteResult, ...]

    @property
    def target_count(self) -> int:
        return len(self.results)

    @property
    def written_count(self) -> int:
        return sum(1 for result in self.results if result.path is not None)

    @property
    def success_count(self) -> int:
        return sum(1 for result in self.results if result.status == "success")

    @property
    def partial_count(self) -> int:
        return sum(1 for result in self.results if result.status == "partial")

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")

    def to_dict(self) -> dict[str, object]:
        return {
            "captured_at_utc": self.captured_at_utc,
            "output_root": str(self.output_root),
            "target_count": self.target_count,
            "written_count": self.written_count,
            "success_count": self.success_count,
            "partial_count": self.partial_count,
            "failed_count": self.failed_count,
            "results": [result.to_dict() for result in self.results],
        }


@dataclass(frozen=True)
class CaptureUploadResult:
    place: str
    status: str
    s3_uri: str | None
    error_sources: tuple[str, ...]
    error_messages: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "place": self.place,
            "status": self.status,
            "s3_uri": self.s3_uri,
            "error_sources": list(self.error_sources),
            "error_messages": list(self.error_messages),
        }


@dataclass(frozen=True)
class S3CollectorRunSummary:
    captured_at_utc: str
    bucket: str
    prefix: str
    profile: str
    results: tuple[CaptureUploadResult, ...]

    @property
    def target_count(self) -> int:
        return len(self.results)

    @property
    def uploaded_count(self) -> int:
        return sum(1 for result in self.results if result.s3_uri is not None)

    @property
    def success_count(self) -> int:
        return sum(1 for result in self.results if result.status == "success")

    @property
    def partial_count(self) -> int:
        return sum(1 for result in self.results if result.status == "partial")

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")

    def to_dict(self) -> dict[str, object]:
        return {
            "captured_at_utc": self.captured_at_utc,
            "bucket": self.bucket,
            "prefix": self.prefix,
            "profile": self.profile,
            "target_count": self.target_count,
            "uploaded_count": self.uploaded_count,
            "success_count": self.success_count,
            "partial_count": self.partial_count,
            "failed_count": self.failed_count,
            "results": [result.to_dict() for result in self.results],
        }


class LiveStudyCollector:
    def __init__(
        self,
        weather_service: WeatherService,
        market_service: KalshiWeatherService,
        *,
        collector_name: str = DEFAULT_COLLECTOR_NAME,
        collector_version: str = DEFAULT_COLLECTOR_VERSION,
    ):
        self._weather_service = weather_service
        self._market_service = market_service
        self._collector_name = collector_name
        self._collector_version = collector_version

    def capture_to_directory(
        self,
        *,
        output_root: str | Path = DEFAULT_OUTPUT_ROOT,
        places: tuple[str, ...] | list[str] | None = None,
        captured_at_utc: datetime | None = None,
    ) -> CollectorRunSummary:
        target_output_root = Path(output_root).expanduser().resolve()
        capture_time = captured_at_utc or parse_capture_time(None)
        results = tuple(
            self._capture_city(
                place_config=place_config,
                output_root=target_output_root,
                captured_at_utc=capture_time,
            )
            for place_config in resolve_study_cities(places)
        )
        return CollectorRunSummary(
            captured_at_utc=capture_time.isoformat().replace("+00:00", "Z"),
            output_root=target_output_root,
            results=results,
        )

    def capture_to_s3(
        self,
        *,
        bucket: str,
        prefix: str = DEFAULT_S3_PREFIX,
        profile: str = DEFAULT_AWS_PROFILE,
        places: tuple[str, ...] | list[str] | None = None,
        captured_at_utc: datetime | None = None,
    ) -> S3CollectorRunSummary:
        normalized_bucket = bucket.strip()
        if not normalized_bucket:
            raise StudyValidationError("--bucket must be a non-empty S3 bucket name.")
        normalized_prefix = prefix.strip().strip("/")
        capture_time = captured_at_utc or parse_capture_time(None)
        with TemporaryDirectory(prefix="weather-study-capture-") as temp_dir:
            temp_root = Path(temp_dir).resolve()
            local_summary = self.capture_to_directory(
                output_root=temp_root,
                places=places,
                captured_at_utc=capture_time,
            )
            uploadable_results = [result for result in local_summary.results if result.path is not None]
            if uploadable_results:
                target_uri = build_s3_prefix_uri(normalized_bucket, normalized_prefix)
                command = [
                    "aws",
                    "s3",
                    "sync",
                    str(temp_root),
                    target_uri,
                    "--profile",
                    profile,
                ]
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
                if completed.returncode != 0:
                    detail = completed.stderr.strip() or completed.stdout.strip() or "unknown AWS CLI error"
                    raise RuntimeError(f"`aws s3 sync` failed for {target_uri}: {detail}")
            upload_results = tuple(
                CaptureUploadResult(
                    place=result.place,
                    status=result.status,
                    s3_uri=(
                        build_s3_object_uri(
                            normalized_bucket,
                            normalized_prefix,
                            Path(result.path).relative_to(temp_root),
                        )
                        if result.path is not None
                        else None
                    ),
                    error_sources=result.error_sources,
                    error_messages=result.error_messages,
                )
                for result in local_summary.results
            )
        return S3CollectorRunSummary(
            captured_at_utc=local_summary.captured_at_utc,
            bucket=normalized_bucket,
            prefix=normalized_prefix,
            profile=profile,
            results=upload_results,
        )

    def _capture_city(
        self,
        *,
        place_config,
        output_root: Path,
        captured_at_utc: datetime,
    ) -> CaptureWriteResult:
        local_timestamp = captured_at_utc.astimezone(ZoneInfo(place_config.timezone))
        local_date = local_timestamp.date().isoformat()
        weather_payload: dict[str, Any] | None = None
        market_payload: dict[str, Any] | None = None
        errors: list[dict[str, str]] = []

        try:
            weather_payload = self._weather_service.fetch(
                place_config.place,
                "rest-of-today",
                now=captured_at_utc,
            )
        except Exception as exc:
            errors.append({"source": "weather", "message": format_error_message(exc)})

        try:
            market_snapshot = self._market_service.fetch_city_ladder(
                place_config.kalshi_city,
                target_date=local_date,
            )
            if market_snapshot.event_date != local_date:
                raise StudyValidationError(
                    "Kalshi active ladder date "
                    f"{market_snapshot.event_date} did not match local capture date {local_date}."
                )
            market_payload = market_snapshot.to_dict()
        except Exception as exc:
            errors.append({"source": "market", "message": format_error_message(exc)})

        if weather_payload is None and market_payload is None:
            return CaptureWriteResult(
                place=place_config.place,
                status="failed",
                path=None,
                error_sources=tuple(entry["source"] for entry in errors),
                error_messages=tuple(entry["message"] for entry in errors),
            )

        payload = {
            "schema_version": SCHEMA_VERSION,
            "captured_at_utc": captured_at_utc.isoformat().replace("+00:00", "Z"),
            "collector": {
                "name": self._collector_name,
                "version": self._collector_version,
            },
            "city": {
                "name": place_config.city,
                "state": place_config.state,
                "place": place_config.place,
                "timezone": place_config.timezone,
            },
            "capture_context": {
                "local_timestamp": local_timestamp.isoformat(),
                "local_date": local_date,
                "local_hour": local_timestamp.hour,
            },
            "weather": {
                "source": "weather-cli rest-of-today",
                "payload": weather_payload,
            },
            "market": {
                "source": "kalshi-weather-markets --format json",
                "payload": market_payload,
            },
            "errors": errors,
        }
        capture = StudyCapture.from_dict(payload)
        relative_path = build_capture_relative_path(capture)
        target_path = output_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(capture.to_dict(), indent=2) + "\n", encoding="utf-8")
        return CaptureWriteResult(
            place=place_config.place,
            status="partial" if errors else "success",
            path=str(target_path),
            error_sources=tuple(entry["source"] for entry in errors),
            error_messages=tuple(entry["message"] for entry in errors),
        )


def build_default_collector(
    *,
    contact_email: str = DEFAULT_CONTACT_EMAIL,
    collector_name: str = DEFAULT_COLLECTOR_NAME,
    collector_version: str = DEFAULT_COLLECTOR_VERSION,
) -> LiveStudyCollector:
    user_agent = f"weather-study-collector/0.1 ({contact_email})"
    http_client = JsonHttpClient(user_agent=user_agent)
    return LiveStudyCollector(
        weather_service=WeatherService(
            geocoder=OpenMeteoGeocoder(http_client),
            noaa_api=NoaaApi(http_client),
        ),
        market_service=KalshiWeatherService(KalshiPublicClient()),
        collector_name=collector_name,
        collector_version=collector_version,
    )


def parse_capture_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(tz=UTC).replace(minute=0, second=0, microsecond=0)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StudyValidationError("--captured-at-utc must be an ISO-8601 UTC timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise StudyValidationError("--captured-at-utc must be in UTC.")
    parsed = parsed.astimezone(UTC)
    if parsed.minute != 0 or parsed.second != 0 or parsed.microsecond != 0:
        raise StudyValidationError("--captured-at-utc must be on the UTC hour.")
    return parsed


def format_error_message(exc: Exception) -> str:
    detail = str(exc).strip() or exc.__class__.__name__
    return f"{exc.__class__.__name__}: {detail}"


def build_s3_prefix_uri(bucket: str, prefix: str) -> str:
    if prefix:
        return f"s3://{bucket}/{prefix}/"
    return f"s3://{bucket}/"


def build_s3_object_uri(bucket: str, prefix: str, relative_path: Path) -> str:
    relative = "/".join(relative_path.parts)
    if prefix:
        return f"s3://{bucket}/{prefix}/{relative}"
    return f"s3://{bucket}/{relative}"
