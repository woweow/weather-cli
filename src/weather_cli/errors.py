class WeatherCliError(Exception):
    """Base exception for CLI failures."""


class HttpRequestError(WeatherCliError):
    """Raised when an HTTP request fails."""


class InputError(WeatherCliError):
    """Raised for invalid user input."""


class GeocodingError(WeatherCliError):
    """Raised when place resolution fails."""


class DataNotFoundError(WeatherCliError):
    """Raised when upstream data is unavailable."""
