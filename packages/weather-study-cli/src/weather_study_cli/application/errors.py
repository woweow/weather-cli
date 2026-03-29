from __future__ import annotations


class WeatherStudyCliError(Exception):
    """Base exception for study CLI failures."""


class StudyValidationError(WeatherStudyCliError):
    """Raised when raw study captures do not match the expected contract."""


class IncompatibleStudyDatabaseError(WeatherStudyCliError):
    """Raised when the local study SQLite schema version is incompatible."""


class DailyActualDerivationError(WeatherStudyCliError):
    """Raised when NOAA-backed daily actual derivation fails."""
