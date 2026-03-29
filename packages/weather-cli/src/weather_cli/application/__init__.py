from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weather_cli.application.service import WeatherService

__all__ = ["WeatherService"]


def __getattr__(name: str):
    if name == "WeatherService":
        from weather_cli.application.service import WeatherService

        return WeatherService
    raise AttributeError(name)
