from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from weather_study_cli.application.errors import StudyValidationError


@dataclass(frozen=True)
class StudyCity:
    city: str
    state: str
    timezone: str
    market_city: str | None = None

    @property
    def place(self) -> str:
        return f"{self.city},{self.state}"

    @property
    def kalshi_city(self) -> str:
        return self.market_city or self.city


SUPPORTED_STUDY_CITIES = (
    StudyCity(city="Seattle", state="WA", timezone="America/Los_Angeles"),
    StudyCity(city="San Francisco", state="CA", timezone="America/Los_Angeles"),
    StudyCity(city="Los Angeles", state="CA", timezone="America/Los_Angeles"),
    StudyCity(city="Las Vegas", state="NV", timezone="America/Los_Angeles"),
    StudyCity(city="Phoenix", state="AZ", timezone="America/Phoenix"),
    StudyCity(city="Denver", state="CO", timezone="America/Denver"),
)


def list_supported_study_places() -> tuple[str, ...]:
    return tuple(city.place for city in SUPPORTED_STUDY_CITIES)


def resolve_study_cities(places: Sequence[str] | None = None) -> tuple[StudyCity, ...]:
    if not places:
        return SUPPORTED_STUDY_CITIES

    supported = {city.place.casefold(): city for city in SUPPORTED_STUDY_CITIES}
    resolved: list[StudyCity] = []
    seen: set[str] = set()
    unsupported: list[str] = []

    for raw_place in places:
        normalized = ",".join(part.strip() for part in raw_place.split(","))
        candidate = supported.get(normalized.casefold())
        if candidate is None:
            unsupported.append(raw_place)
            continue
        key = candidate.place.casefold()
        if key in seen:
            continue
        seen.add(key)
        resolved.append(candidate)

    if unsupported:
        supported_places = ", ".join(list_supported_study_places())
        joined = ", ".join(unsupported)
        raise StudyValidationError(f"Unsupported study city selection: {joined}. Use one of: {supported_places}")

    return tuple(resolved)
