from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from kalshi_weather_markets_cli.errors import KalshiHttpError


BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiPublicClient:
    def __init__(self, base_url: str = BASE_URL, timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.user_agent = "kalshi-weather-markets-cli/0.1"

    def list_series(self, category: str = "Climate and Weather") -> list[dict]:
        payload = self._get_json("/series", {"category": category})
        return payload.get("series", [])

    def get_markets(
        self,
        series_ticker: str,
        *,
        status: str = "open",
        limit: int = 1000,
    ) -> list[dict]:
        payload = self._get_json(
            "/markets",
            {
                "series_ticker": series_ticker,
                "status": status,
                "limit": limit,
            },
        )
        return payload.get("markets", [])

    def _get_json(self, path: str, params: dict[str, object] | None = None) -> dict:
        query = urlencode(params or {})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.load(response)
        except HTTPError as exc:
            detail = exc.reason
            try:
                payload = json.load(exc)
            except Exception:
                payload = None
            if isinstance(payload, dict):
                error = payload.get("error") or {}
                detail = error.get("message") or detail
            raise KalshiHttpError(f"Kalshi API request failed: {detail}") from exc
        except URLError as exc:
            raise KalshiHttpError(f"Kalshi API request failed: {exc.reason}") from exc
