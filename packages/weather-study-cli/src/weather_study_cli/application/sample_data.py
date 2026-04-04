from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from weather_study_cli.application.actuals import (
    DEFAULT_CONTACT_EMAIL,
    ObservedHighService,
    build_weather_service,
)
from weather_study_cli.application.cities import StudyCity, resolve_study_cities
from weather_study_cli.application.errors import S3SyncError, StudyValidationError
from weather_study_cli.application.market_utils import round_half_up
from weather_study_cli.application.raw_loader import DEFAULT_MOCK_DATA_DIR, build_capture_relative_path
from weather_study_cli.application.raw_schema import StudyCapture
from weather_study_cli.application.s3 import DEFAULT_AWS_PROFILE, build_aws_s3_sync_command


DEFAULT_SAMPLE_OUTPUT_ROOT = DEFAULT_MOCK_DATA_DIR
DEFAULT_SAMPLE_METADATA_PATH = DEFAULT_MOCK_DATA_DIR.parent / "sample-week-metadata.json"
DEFAULT_SAMPLE_PLACES = ("Seattle,WA", "Denver,CO")
DEFAULT_SAMPLE_DAY_COUNT = 7
DEFAULT_SAMPLE_S3_PREFIX = "sample/weather-study-weekly"
DEFAULT_SAMPLE_COLLECTOR_NAME = "weather-market-study-sample"
DEFAULT_SAMPLE_COLLECTOR_VERSION = "2"

_LOCK_IN_HOURS_BY_PLACE = {
    "Seattle,WA": (10, 11, 12, 12, 13, 14, 14),
    "Denver,CO": (9, 10, 11, 11, 12, 13, 14),
}


@dataclass(frozen=True)
class SampleDataGenerationSummary:
    output_root: Path
    metadata_path: Path
    places: tuple[str, ...]
    local_dates: tuple[str, ...]
    capture_count: int
    bucket: str | None
    prefix: str | None
    profile: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "output_root": str(self.output_root),
            "metadata_path": str(self.metadata_path),
            "places": list(self.places),
            "local_dates": list(self.local_dates),
            "capture_count": self.capture_count,
            "bucket": self.bucket,
            "prefix": self.prefix,
            "profile": self.profile,
        }


def generate_sample_capture_directory(
    *,
    output_root: str | Path = DEFAULT_SAMPLE_OUTPUT_ROOT,
    metadata_path: str | Path = DEFAULT_SAMPLE_METADATA_PATH,
    places: tuple[str, ...] | list[str] | None = None,
    day_count: int = DEFAULT_SAMPLE_DAY_COUNT,
    end_local_date: str | None = None,
    bucket: str | None = None,
    prefix: str = DEFAULT_SAMPLE_S3_PREFIX,
    profile: str = DEFAULT_AWS_PROFILE,
    contact_email: str = DEFAULT_CONTACT_EMAIL,
    now: datetime | None = None,
    weather_service: ObservedHighService | None = None,
) -> SampleDataGenerationSummary:
    if day_count <= 0:
        raise StudyValidationError("--day-count must be at least 1.")

    cities = resolve_study_cities(places or DEFAULT_SAMPLE_PLACES)
    generation_now = now or datetime.now(tz=UTC)
    common_end_date = _resolve_common_end_local_date(cities, generation_now, end_local_date)
    local_dates = tuple(
        (common_end_date - timedelta(days=offset)).isoformat()
        for offset in range(day_count - 1, -1, -1)
    )
    target_output_root = Path(output_root).expanduser().resolve()
    target_metadata_path = Path(metadata_path).expanduser().resolve()
    service = weather_service or build_weather_service(contact_email)
    actual_highs = _fetch_actual_highs(service, cities, local_dates)

    if target_output_root.exists():
        shutil.rmtree(target_output_root)
    target_output_root.mkdir(parents=True, exist_ok=True)

    capture_count = 0
    lock_in_manifest: dict[str, dict[str, int]] = {}
    for city in cities:
        lock_in_hours = _lock_in_hours_for_city(city.place, len(local_dates))
        lock_in_manifest[city.place] = {
            local_date: lock_in_hour
            for local_date, lock_in_hour in zip(local_dates, lock_in_hours, strict=True)
        }
        for day_index, local_date in enumerate(local_dates):
            actual_high = actual_highs[city.place][local_date]
            for local_hour in range(24):
                capture = _build_sample_capture(
                    city=city,
                    local_date=local_date,
                    local_hour=local_hour,
                    actual_high=actual_high,
                    lock_in_hour=lock_in_hours[day_index],
                    day_index=day_index,
                )
                relative_path = build_capture_relative_path(capture)
                target_path = target_output_root / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(json.dumps(capture.to_dict(), indent=2) + "\n", encoding="utf-8")
                capture_count += 1

    metadata = {
        "generated_at_utc": generation_now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "places": [city.place for city in cities],
        "local_dates": list(local_dates),
        "actual_highs_f": actual_highs,
        "lock_in_hours": lock_in_manifest,
        "capture_count": capture_count,
        "notes": {
            "description": (
                "Seven completed local days of hourly synthetic captures for study-report demos. "
                "Daily actual highs come from NOAA observed highs; forecasts and market ladders are synthetic "
                "and intentionally converge toward the observed winner through the day."
            ),
        },
    }
    target_metadata_path.parent.mkdir(parents=True, exist_ok=True)
    target_metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    normalized_bucket = None
    normalized_prefix = None
    normalized_profile = None
    if bucket is not None:
        normalized_bucket = bucket.strip()
        if not normalized_bucket:
            raise StudyValidationError("--bucket must be a non-empty S3 bucket name.")
        normalized_prefix = prefix.strip().strip("/")
        normalized_profile = profile
        _upload_sample_directory_to_s3(
            target_output_root,
            bucket=normalized_bucket,
            prefix=normalized_prefix,
            profile=normalized_profile,
        )

    return SampleDataGenerationSummary(
        output_root=target_output_root,
        metadata_path=target_metadata_path,
        places=tuple(city.place for city in cities),
        local_dates=local_dates,
        capture_count=capture_count,
        bucket=normalized_bucket,
        prefix=normalized_prefix,
        profile=normalized_profile,
    )


def _resolve_common_end_local_date(
    cities: tuple[StudyCity, ...],
    now: datetime,
    end_local_date: str | None,
) -> date:
    if end_local_date is not None:
        return date.fromisoformat(end_local_date)
    completed_dates = [
        now.astimezone(ZoneInfo(city.timezone)).date() - timedelta(days=1)
        for city in cities
    ]
    return min(completed_dates)


def _fetch_actual_highs(
    service: ObservedHighService,
    cities: tuple[StudyCity, ...],
    local_dates: tuple[str, ...],
) -> dict[str, dict[str, float]]:
    actual_highs: dict[str, dict[str, float]] = {}
    for city in cities:
        by_date: dict[str, float] = {}
        for local_date in local_dates:
            payload = service.fetch_observed_high_for_date(city.place, local_date)
            by_date[local_date] = float(payload["observed_high_temperature_f"])
        actual_highs[city.place] = by_date
    return actual_highs


def _lock_in_hours_for_city(place: str, day_count: int) -> tuple[int, ...]:
    configured = _LOCK_IN_HOURS_BY_PLACE.get(place)
    if configured is None:
        base = tuple(9 + min(index, 5) for index in range(day_count))
        return base
    if len(configured) == day_count:
        return configured
    if len(configured) > day_count:
        return configured[:day_count]
    repeated = list(configured)
    while len(repeated) < day_count:
        repeated.append(repeated[-1])
    return tuple(repeated)


def _build_sample_capture(
    *,
    city: StudyCity,
    local_date: str,
    local_hour: int,
    actual_high: float,
    lock_in_hour: int,
    day_index: int,
) -> StudyCapture:
    zone = ZoneInfo(city.timezone)
    local_timestamp = datetime.combine(date.fromisoformat(local_date), time(local_hour, 0), tzinfo=zone)
    captured_at_utc = local_timestamp.astimezone(UTC)
    rounded_actual = round_half_up(actual_high)
    forecast_high = _sample_forecast_high(
        rounded_actual=rounded_actual,
        local_hour=local_hour,
        lock_in_hour=lock_in_hour,
        day_index=day_index,
        city_seed=sum(ord(char) for char in city.place),
    )
    payload = {
        "schema_version": "1",
        "captured_at_utc": captured_at_utc.isoformat().replace("+00:00", "Z"),
        "collector": {
            "name": DEFAULT_SAMPLE_COLLECTOR_NAME,
            "version": DEFAULT_SAMPLE_COLLECTOR_VERSION,
        },
        "city": {
            "name": city.city,
            "state": city.state,
            "place": city.place,
            "timezone": city.timezone,
        },
        "capture_context": {
            "local_timestamp": local_timestamp.isoformat(),
            "local_date": local_date,
            "local_hour": local_hour,
        },
        "weather": {
            "source": "sample-generator rest-of-today",
            "payload": _build_weather_payload(city, local_timestamp, forecast_high),
        },
        "market": {
            "source": "sample-generator kalshi-ladder",
            "payload": _build_market_payload(
                city=city,
                local_date=local_date,
                local_hour=local_hour,
                rounded_actual=rounded_actual,
                lock_in_hour=lock_in_hour,
                day_index=day_index,
            ),
        },
        "errors": [],
    }
    return StudyCapture.from_dict(payload)


def _sample_forecast_high(
    *,
    rounded_actual: int,
    local_hour: int,
    lock_in_hour: int,
    day_index: int,
    city_seed: int,
) -> int:
    if local_hour >= lock_in_hour:
        return rounded_actual
    distance_hours = max(1, lock_in_hour - local_hour)
    offset_steps = min(4, max(1, (distance_hours + 1) // 2))
    offset = offset_steps * 2
    sign = 1 if (day_index + local_hour + city_seed) % 2 == 0 else -1
    candidate = rounded_actual + (offset * sign)
    if candidate == rounded_actual:
        candidate += 2
    return candidate


def _build_weather_payload(city: StudyCity, local_timestamp: datetime, forecast_high: int) -> dict[str, Any]:
    local_midnight = local_timestamp.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    period_end = min(local_timestamp + timedelta(hours=1), local_midnight)
    return {
        "location": {
            "input": city.place,
            "city": city.city,
            "state": city.state,
            "timezone": city.timezone,
        },
        "resolved_coordinates": {
            "latitude": None,
            "longitude": None,
        },
        "range": {
            "name": "rest-of-today",
            "mode": "forecast",
            "start": local_timestamp.isoformat(),
            "end": local_midnight.isoformat(),
        },
        "source": {
            "geocoder": "sample-generator",
            "provider": "sample-generator",
            "point_url": "sample://point",
            "station_selection": "sample",
            "forecast_url": "sample://forecast",
        },
        "station": {
            "identifier": "SAMPLE",
            "name": f"{city.city} Sample Station",
            "timezone": city.timezone,
            "distance_meters": 0,
            "latitude": None,
            "longitude": None,
        },
        "periods": [
            {
                "kind": "forecast",
                "start": local_timestamp.isoformat(),
                "end": period_end.isoformat(),
                "temperature_f": forecast_high,
                "relative_humidity_pct": 55,
                "precipitation_probability_pct": 10,
                "wind_speed": "6 mph",
                "wind_direction": "NW",
                "summary": "Sample Forecast",
                "is_daytime": 6 <= local_timestamp.hour < 19,
            }
        ],
    }


def _build_market_payload(
    *,
    city: StudyCity,
    local_date: str,
    local_hour: int,
    rounded_actual: int,
    lock_in_hour: int,
    day_index: int,
) -> dict[str, Any]:
    series_code = _market_series_code(city)
    event_token = date.fromisoformat(local_date).strftime("%d%b%y").upper()
    event_ticker = f"KXHIGHT{series_code}-{event_token}"
    winner_floor = _winning_bucket_floor(rounded_actual)
    winner_price_cents = _winner_price_cents(local_hour=local_hour, lock_in_hour=lock_in_hour, day_index=day_index)
    market_rows = _build_market_rows(
        event_ticker=event_ticker,
        winner_floor=winner_floor,
        winner_price_cents=winner_price_cents,
    )
    return {
        "provider": "kalshi",
        "city": city.city,
        "series_ticker": f"KXHIGHT{series_code}",
        "series_title": f"{city.city} Maximum Temperature Daily",
        "event_ticker": event_ticker,
        "event_date": local_date,
        "event_date_label": _format_event_date_label(local_date),
        "markets": market_rows,
    }


def _market_series_code(city: StudyCity) -> str:
    condensed = "".join(char for char in city.city.upper() if char.isalpha())
    return condensed[:3]


def _format_event_date_label(local_date: str) -> str:
    parsed = date.fromisoformat(local_date)
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"


def _winning_bucket_floor(rounded_actual: int) -> int:
    return rounded_actual if rounded_actual % 2 == 1 else rounded_actual - 1


def _winner_price_cents(*, local_hour: int, lock_in_hour: int, day_index: int) -> int:
    if local_hour < lock_in_hour:
        progress = local_hour / max(lock_in_hour, 1)
        return _normalize_price(18 + int(progress * 24) + day_index)
    settled_progress = local_hour - lock_in_hour
    return _normalize_price(62 + (settled_progress * 6) + day_index)


def _build_market_rows(
    *,
    event_ticker: str,
    winner_floor: int,
    winner_price_cents: int,
) -> list[dict[str, Any]]:
    floors = [winner_floor + (offset * 2) for offset in range(-3, 4)]
    winning_index = 3
    rows: list[dict[str, Any]] = []

    low_cap = floors[0] - 1
    high_floor = floors[-1] + 2
    boundary_rows = [
        {
            "ticker": f"{event_ticker}-LT{low_cap}",
            "title": f"{low_cap} or below",
            "label": f"{low_cap}F or below",
            "sort_key": float(low_cap),
        },
        None,
        {
            "ticker": f"{event_ticker}-GT{high_floor}",
            "title": f"{high_floor} or above",
            "label": f"{high_floor}F or above",
            "sort_key": float(high_floor),
        },
    ]

    rows.append(_decorate_market_row(boundary_rows[0], _adjacent_bucket_price(winner_price_cents, 4)))
    for index, floor in enumerate(floors):
        title = f"{floor} to {floor + 1}"
        base_row = {
            "ticker": f"{event_ticker}-B{floor + 0.5:.1f}",
            "title": title,
            "label": f"{floor}F to {floor + 1}F",
            "sort_key": float(floor) + 0.5,
        }
        price = winner_price_cents if index == winning_index else _adjacent_bucket_price(
            winner_price_cents,
            abs(index - winning_index),
        )
        rows.append(_decorate_market_row(base_row, price))
    rows.append(_decorate_market_row(boundary_rows[2], _adjacent_bucket_price(winner_price_cents, 4)))
    return rows


def _adjacent_bucket_price(winner_price_cents: int, distance: int) -> int:
    return _normalize_price(winner_price_cents - (distance * 14) - 6)


def _decorate_market_row(base_row: dict[str, Any], last_price_cents: int) -> dict[str, Any]:
    yes_bid_cents = _normalize_price(last_price_cents - 1)
    yes_ask_cents = _normalize_price(last_price_cents + 1)
    return {
        **base_row,
        "yes_bid_cents": yes_bid_cents,
        "yes_ask_cents": yes_ask_cents,
        "no_bid_cents": _normalize_price(100 - yes_ask_cents),
        "no_ask_cents": _normalize_price(100 - yes_bid_cents),
        "last_price_cents": last_price_cents,
    }


def _normalize_price(value: int) -> int:
    return max(1, min(99, value))


def _upload_sample_directory_to_s3(
    output_root: Path,
    *,
    bucket: str,
    prefix: str,
    profile: str,
) -> None:
    target_uri = _build_s3_target_uri(bucket, prefix)
    command = build_aws_s3_sync_command(
        source=str(output_root),
        destination=target_uri,
        profile=profile,
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown AWS CLI error"
        raise S3SyncError(f"`aws s3 sync` failed for {target_uri}: {detail}")


def _build_s3_target_uri(bucket: str, prefix: str) -> str:
    if prefix:
        return f"s3://{bucket}/{prefix}/"
    return f"s3://{bucket}/"
