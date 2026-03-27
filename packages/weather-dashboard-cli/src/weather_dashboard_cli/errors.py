from __future__ import annotations


class WeatherDashboardCliError(Exception):
    """Base error for dashboard CLI failures."""


class PayloadValidationError(WeatherDashboardCliError):
    """Raised when normalized dashboard JSON does not match the required shape."""
