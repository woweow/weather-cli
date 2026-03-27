from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from weather_cli.errors import InputError


UTC = ZoneInfo("UTC")
VALID_RANGES = ("yesterday", "today", "previous-24h", "next-24h")


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
    mode = "forecast" if range_name == "next-24h" else "observations"

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


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
