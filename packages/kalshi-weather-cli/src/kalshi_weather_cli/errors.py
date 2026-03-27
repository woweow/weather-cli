class KalshiWeatherCliError(Exception):
    """Base error for the Kalshi weather CLI."""


class KalshiHttpError(KalshiWeatherCliError):
    """Kalshi returned an HTTP or transport error."""


class UnsupportedCityError(KalshiWeatherCliError):
    """The requested city does not map to a supported Kalshi series."""


class MarketDataError(KalshiWeatherCliError):
    """Market data was missing or unusable."""
