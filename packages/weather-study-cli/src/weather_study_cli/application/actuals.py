from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from weather_cli.adapters.geocoding import OpenMeteoGeocoder
from weather_cli.adapters.http import JsonHttpClient
from weather_cli.adapters.noaa import NoaaApi
from weather_cli.application.errors import WeatherCliError
from weather_cli.application.service import WeatherService
from weather_study_cli.application.errors import DailyActualDerivationError
from weather_study_cli.persistence.connection import DEFAULT_DB_PATH, open_connection
from weather_study_cli.persistence.migrations import initialize_schema
from weather_study_cli.persistence.repository import (
    get_table_counts,
    list_daily_actual_targets,
    upsert_daily_actual,
)


DEFAULT_CONTACT_EMAIL = os.getenv("WEATHER_CLI_CONTACT_EMAIL", "weather-study@example.com")


class ObservedHighService(Protocol):
    def fetch_observed_high_for_date(
        self,
        place: str,
        event_date: str,
        *,
        station_override: str | None = None,
        use_station_presets: bool = True,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class DailyActualDerivationSummary:
    db_path: Path
    target_count: int
    resolved_count: int
    skipped_incomplete_count: int
    daily_actual_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "db_path": str(self.db_path),
            "target_count": self.target_count,
            "resolved_count": self.resolved_count,
            "skipped_incomplete_count": self.skipped_incomplete_count,
            "daily_actual_count": self.daily_actual_count,
        }


def derive_daily_actuals(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    place: str | None = None,
    local_date: str | None = None,
    contact_email: str = DEFAULT_CONTACT_EMAIL,
    now: datetime | None = None,
    weather_service: ObservedHighService | None = None,
) -> DailyActualDerivationSummary:
    target_db_path = Path(db_path).expanduser().resolve()
    now_utc = now or datetime.now(tz=UTC)
    if now_utc.tzinfo is None:
        raise DailyActualDerivationError("The supplied 'now' value must be timezone-aware.")

    service = weather_service or build_weather_service(contact_email)

    with open_connection(target_db_path) as connection:
        initialize_schema(connection)
        targets = list_daily_actual_targets(connection, place=place, local_date=local_date)
        resolved_count = 0
        skipped_incomplete_count = 0

        for target in targets:
            if not is_completed_local_day(target["local_date"], target["timezone"], now_utc):
                skipped_incomplete_count += 1
                continue
            try:
                payload = service.fetch_observed_high_for_date(target["place"], target["local_date"])
            except WeatherCliError as exc:
                raise DailyActualDerivationError(
                    f"Failed to derive actual high for {target['place']} on {target['local_date']}: {exc}"
                ) from exc
            upsert_daily_actual(
                connection,
                place=target["place"],
                local_date=target["local_date"],
                timezone=target["timezone"],
                observed_high_temperature_f=payload["observed_high_temperature_f"],
                observed_payload=payload,
                resolved_at_utc=now_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            )
            resolved_count += 1

        connection.commit()
        counts = get_table_counts(connection)

    return DailyActualDerivationSummary(
        db_path=target_db_path,
        target_count=len(targets),
        resolved_count=resolved_count,
        skipped_incomplete_count=skipped_incomplete_count,
        daily_actual_count=counts["daily_actuals"],
    )


def build_weather_service(contact_email: str) -> WeatherService:
    user_agent = f"weather-study-cli/0.1 ({contact_email})"
    return WeatherService(
        geocoder=OpenMeteoGeocoder(JsonHttpClient(user_agent=user_agent)),
        noaa_api=NoaaApi(JsonHttpClient(user_agent=user_agent)),
    )


def is_completed_local_day(local_date_text: str, timezone: str, now: datetime) -> bool:
    target_date = date.fromisoformat(local_date_text)
    local_now = now.astimezone(ZoneInfo(timezone))
    return local_now.date() > target_date
