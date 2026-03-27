from __future__ import annotations


class WeatherBetsError(Exception):
    """Base error for the local weather bet journal."""


class SnapshotValidationError(WeatherBetsError):
    """Raised when dashboard JSON does not match the required decision snapshot shape."""


class BetSelectionNotFoundError(WeatherBetsError):
    """Raised when a requested bet selection does not exist."""
