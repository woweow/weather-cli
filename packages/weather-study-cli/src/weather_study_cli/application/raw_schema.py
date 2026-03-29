from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from weather_study_cli.application.errors import StudyValidationError


VALID_ERROR_SOURCES = {"weather", "market", "collector"}


@dataclass(frozen=True)
class CapturePathMetadata:
    study_version: str
    city: str
    state: str
    local_date: str
    local_hour: int
    captured_at_utc: str


@dataclass(frozen=True)
class CaptureError:
    source: str
    message: str

    @classmethod
    def from_dict(cls, payload: Any, *, field_name: str) -> "CaptureError":
        data = _require_dict(payload, field_name)
        source = _require_str(data.get("source"), f"{field_name}.source")
        if source not in VALID_ERROR_SOURCES:
            supported = ", ".join(sorted(VALID_ERROR_SOURCES))
            raise StudyValidationError(f"{field_name}.source must be one of {supported}, got {source!r}.")
        message = _require_str(data.get("message"), f"{field_name}.message")
        return cls(source=source, message=message)


@dataclass(frozen=True)
class CaptureSource:
    source: str
    payload: dict[str, Any] | None

    @classmethod
    def from_dict(cls, payload: Any, *, field_name: str) -> "CaptureSource":
        data = _require_dict(payload, field_name)
        source = _require_str(data.get("source"), f"{field_name}.source")
        raw_payload = data.get("payload")
        if raw_payload is not None and not isinstance(raw_payload, dict):
            raise StudyValidationError(f"{field_name}.payload must be an object or null.")
        return cls(source=source, payload=raw_payload)


@dataclass(frozen=True)
class StudyCapture:
    schema_version: str
    captured_at_utc: str
    collector_name: str
    collector_version: str
    city_name: str
    state_code: str
    place: str
    timezone: str
    local_timestamp: str
    local_date: str
    local_hour: int
    weather: CaptureSource
    market: CaptureSource
    errors: tuple[CaptureError, ...]
    source_path: Path | None = None

    @property
    def city_key(self) -> str:
        return self.place

    @property
    def has_weather(self) -> bool:
        return self.weather.payload is not None

    @property
    def has_market(self) -> bool:
        return self.market.payload is not None

    @property
    def error_sources(self) -> set[str]:
        return {entry.source for entry in self.errors}

    @classmethod
    def from_dict(
        cls,
        payload: Any,
        *,
        path_metadata: CapturePathMetadata | None = None,
        source_path: Path | None = None,
    ) -> "StudyCapture":
        data = _require_dict(payload, "root")
        schema_version = _require_str(data.get("schema_version"), "schema_version")
        captured_at = _parse_datetime(
            _require_str(data.get("captured_at_utc"), "captured_at_utc"),
            "captured_at_utc",
            require_utc=True,
        )

        collector = _require_dict(data.get("collector"), "collector")
        collector_name = _require_str(collector.get("name"), "collector.name")
        collector_version = _require_str(collector.get("version"), "collector.version")

        city = _require_dict(data.get("city"), "city")
        city_name = _require_str(city.get("name"), "city.name")
        state_code = _require_str(city.get("state"), "city.state")
        place = _require_str(city.get("place"), "city.place")
        timezone = _require_str(city.get("timezone"), "city.timezone")

        capture_context = _require_dict(data.get("capture_context"), "capture_context")
        local_timestamp_text = _require_str(capture_context.get("local_timestamp"), "capture_context.local_timestamp")
        local_timestamp = _parse_datetime(
            local_timestamp_text,
            "capture_context.local_timestamp",
            require_utc=False,
        )
        local_date_text = _require_str(capture_context.get("local_date"), "capture_context.local_date")
        local_date_value = _parse_date(local_date_text, "capture_context.local_date")
        local_hour = _require_int(capture_context.get("local_hour"), "capture_context.local_hour")
        if not 0 <= local_hour <= 23:
            raise StudyValidationError("capture_context.local_hour must be between 0 and 23.")

        expected_place = f"{city_name},{state_code}"
        if place != expected_place:
            raise StudyValidationError(f"city.place must equal {expected_place!r}, got {place!r}.")
        if local_timestamp.date() != local_date_value:
            raise StudyValidationError(
                "capture_context.local_timestamp date must match capture_context.local_date."
            )
        if local_timestamp.hour != local_hour:
            raise StudyValidationError(
                "capture_context.local_timestamp hour must match capture_context.local_hour."
            )
        if local_timestamp.astimezone(UTC) != captured_at:
            raise StudyValidationError(
                "captured_at_utc must match capture_context.local_timestamp converted to UTC."
            )

        weather = CaptureSource.from_dict(data.get("weather"), field_name="weather")
        market = CaptureSource.from_dict(data.get("market"), field_name="market")
        errors = tuple(
            CaptureError.from_dict(item, field_name=f"errors[{index}]")
            for index, item in enumerate(_require_list(data.get("errors"), "errors"))
        )

        capture = cls(
            schema_version=schema_version,
            captured_at_utc=local_timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            collector_name=collector_name,
            collector_version=collector_version,
            city_name=city_name,
            state_code=state_code,
            place=place,
            timezone=timezone,
            local_timestamp=local_timestamp.isoformat(),
            local_date=local_date_text,
            local_hour=local_hour,
            weather=weather,
            market=market,
            errors=errors,
            source_path=source_path,
        )
        capture._validate_partial_failures()
        capture._validate_weather_payload(local_timestamp)
        capture._validate_market_payload()
        if path_metadata is not None:
            capture._validate_path_metadata(path_metadata)
        return capture

    def _validate_partial_failures(self) -> None:
        if not self.has_weather and not self.has_market:
            raise StudyValidationError("At least one of weather.payload or market.payload must be present.")
        if not self.has_weather and "weather" not in self.error_sources:
            raise StudyValidationError("weather.payload may be null only when errors includes a weather entry.")
        if not self.has_market and "market" not in self.error_sources:
            raise StudyValidationError("market.payload may be null only when errors includes a market entry.")

    def _validate_weather_payload(self, local_timestamp: datetime) -> None:
        if self.weather.payload is None:
            return
        payload = self.weather.payload
        location = _require_dict(payload.get("location"), "weather.payload.location")
        if _require_str(location.get("city"), "weather.payload.location.city") != self.city_name:
            raise StudyValidationError("weather.payload.location.city must match city.name.")
        if _require_str(location.get("state"), "weather.payload.location.state") != self.state_code:
            raise StudyValidationError("weather.payload.location.state must match city.state.")
        if _require_str(location.get("timezone"), "weather.payload.location.timezone") != self.timezone:
            raise StudyValidationError("weather.payload.location.timezone must match city.timezone.")

        range_info = _require_dict(payload.get("range"), "weather.payload.range")
        if _require_str(range_info.get("name"), "weather.payload.range.name") != "rest-of-today":
            raise StudyValidationError("weather.payload.range.name must be 'rest-of-today'.")
        if _require_str(range_info.get("mode"), "weather.payload.range.mode") != "forecast":
            raise StudyValidationError("weather.payload.range.mode must be 'forecast'.")
        range_start = _parse_datetime(
            _require_str(range_info.get("start"), "weather.payload.range.start"),
            "weather.payload.range.start",
            require_utc=False,
        )
        range_end = _parse_datetime(
            _require_str(range_info.get("end"), "weather.payload.range.end"),
            "weather.payload.range.end",
            require_utc=False,
        )
        expected_end = local_timestamp.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if range_start != local_timestamp:
            raise StudyValidationError("weather.payload.range.start must equal capture_context.local_timestamp.")
        if range_end != expected_end:
            raise StudyValidationError("weather.payload.range.end must equal local midnight after the capture.")

        periods = _require_list(payload.get("periods"), "weather.payload.periods")
        if not periods:
            raise StudyValidationError("weather.payload.periods must be non-empty when weather.payload is present.")
        for index, item in enumerate(periods):
            period = _require_dict(item, f"weather.payload.periods[{index}]")
            kind = _require_str(period.get("kind"), f"weather.payload.periods[{index}].kind")
            if kind != "forecast":
                raise StudyValidationError(f"weather.payload.periods[{index}].kind must be 'forecast'.")
            start = _parse_datetime(
                _require_str(period.get("start"), f"weather.payload.periods[{index}].start"),
                f"weather.payload.periods[{index}].start",
                require_utc=False,
            )
            end = _parse_datetime(
                _require_str(period.get("end"), f"weather.payload.periods[{index}].end"),
                f"weather.payload.periods[{index}].end",
                require_utc=False,
            )
            if end <= local_timestamp:
                raise StudyValidationError(
                    f"weather.payload.periods[{index}] must end after capture_context.local_timestamp."
                )
            if start < local_timestamp:
                raise StudyValidationError(
                    f"weather.payload.periods[{index}] must start at or after capture_context.local_timestamp."
                )
            if start.date().isoformat() != self.local_date:
                raise StudyValidationError(
                    f"weather.payload.periods[{index}].start must stay on capture_context.local_date."
                )
            if end > expected_end:
                raise StudyValidationError(
                    f"weather.payload.periods[{index}].end must not extend beyond local midnight."
                )

    def _validate_market_payload(self) -> None:
        if self.market.payload is None:
            return
        payload = self.market.payload
        if _require_str(payload.get("provider"), "market.payload.provider") != "kalshi":
            raise StudyValidationError("market.payload.provider must be 'kalshi'.")
        if _require_str(payload.get("city"), "market.payload.city") != self.city_name:
            raise StudyValidationError("market.payload.city must match city.name.")
        _require_str(payload.get("series_ticker"), "market.payload.series_ticker")
        _require_str(payload.get("series_title"), "market.payload.series_title")
        _require_str(payload.get("event_ticker"), "market.payload.event_ticker")
        if _require_str(payload.get("event_date"), "market.payload.event_date") != self.local_date:
            raise StudyValidationError("market.payload.event_date must match capture_context.local_date.")
        _require_str(payload.get("event_date_label"), "market.payload.event_date_label")
        markets = _require_list(payload.get("markets"), "market.payload.markets")
        if not markets:
            raise StudyValidationError("market.payload.markets must be non-empty when market.payload is present.")
        for index, item in enumerate(markets):
            market = _require_dict(item, f"market.payload.markets[{index}]")
            _require_str(market.get("ticker"), f"market.payload.markets[{index}].ticker")
            _require_str(market.get("label"), f"market.payload.markets[{index}].label")

    def _validate_path_metadata(self, metadata: CapturePathMetadata) -> None:
        if self.schema_version != metadata.study_version:
            raise StudyValidationError("schema_version must match the study_version path segment.")
        if self.city_name != metadata.city:
            raise StudyValidationError("city.name must match the city path segment.")
        if self.state_code != metadata.state:
            raise StudyValidationError("city.state must match the state path segment.")
        if self.local_date != metadata.local_date:
            raise StudyValidationError("capture_context.local_date must match the local_date path segment.")
        if self.local_hour != metadata.local_hour:
            raise StudyValidationError("capture_context.local_hour must match the local_hour path segment.")
        if self.captured_at_utc != metadata.captured_at_utc:
            raise StudyValidationError("captured_at_utc must match the captured_at_utc filename.")


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StudyValidationError(f"{field_name} must be an object.")
    return value


def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise StudyValidationError(f"{field_name} must be a list.")
    return value


def _require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StudyValidationError(f"{field_name} must be a non-empty string.")
    return value


def _require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StudyValidationError(f"{field_name} must be an integer.")
    return value


def _parse_datetime(value: str, field_name: str, *, require_utc: bool) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StudyValidationError(f"{field_name} must be an ISO-8601 datetime.") from exc
    if parsed.tzinfo is None:
        raise StudyValidationError(f"{field_name} must include a timezone offset.")
    if require_utc and parsed.utcoffset() != timedelta(0):
        raise StudyValidationError(f"{field_name} must be in UTC.")
    return parsed


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise StudyValidationError(f"{field_name} must use YYYY-MM-DD format.") from exc
