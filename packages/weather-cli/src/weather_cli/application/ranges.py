from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from weather_cli.application.errors import InputError


UTC = ZoneInfo("UTC")
VALID_RANGES = ("yesterday", "today", "previous-24h", "next-24h", "rest-of-today")


@dataclass(frozen=True)
class TimeWindow:
    name: str
    mode: str
    timezone: str
    start: datetime
    end: datetime

    def contains(self, timestamp: datetime) -> bool:
        return self.start <= timestamp < self.end


def resolve_time_window(range_name: str, timezone: str, now: datetime | None = None) -> TimeWindow:
    if range_name not in VALID_RANGES:
        raise InputError(f"Unsupported range {range_name!r}. Expected one of: {', '.join(VALID_RANGES)}")

    zone = ZoneInfo(timezone)
    if now is None:
        now = datetime.now(tz=UTC)
    if now.tzinfo is None:
        raise InputError("The supplied 'now' value must be timezone-aware.")

    local_now = now.astimezone(zone)
    mode = "forecast" if range_name in {"next-24h", "rest-of-today"} else "observations"

    if range_name == "yesterday":
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = today_start - timedelta(days=1)
        end = today_start
    elif range_name == "today":
        start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = local_now
    elif range_name == "previous-24h":
        end = local_now
        start = local_now - timedelta(hours=24)
    elif range_name == "rest-of-today":
        start = local_now
        end = local_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        start = local_now
        end = local_now + timedelta(hours=24)

    return TimeWindow(
        name=range_name,
        mode=mode,
        timezone=timezone,
        start=start,
        end=end,
    )


def resolve_local_day_window(date_iso: str, timezone: str) -> TimeWindow:
    zone = ZoneInfo(timezone)
    try:
        start = datetime.strptime(date_iso, "%Y-%m-%d").replace(tzinfo=zone)
    except ValueError as exc:
        raise InputError(f"Date must use YYYY-MM-DD format, got {date_iso!r}") from exc
    end = start + timedelta(days=1)
    return TimeWindow(
        name=date_iso,
        mode="observations",
        timezone=timezone,
        start=start,
        end=end,
    )


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
