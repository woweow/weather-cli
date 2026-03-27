from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen

from weather_cli.errors import HttpRequestError


DEFAULT_ACCEPT = "application/geo+json, application/ld+json, application/json"


def build_url(url: str, params: dict[str, Any] | None = None) -> str:
    if not params:
        return url
    split = urlsplit(url)
    pairs = parse_qsl(split.query, keep_blank_values=True)
    for key, value in params.items():
        if value is None:
            continue
        pairs.append((key, str(value)))
    query = urlencode(pairs, doseq=True)
    return urlunsplit((split.scheme, split.netloc, split.path, query, split.fragment))


class JsonHttpClient:
    def __init__(self, user_agent: str, timeout: int = 20):
        self._user_agent = user_agent
        self._timeout = timeout

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        request_headers = {
            "User-Agent": self._user_agent,
            "Accept": DEFAULT_ACCEPT,
        }
        if headers:
            request_headers.update(headers)

        request = Request(build_url(url, params), headers=request_headers)
        try:
            with urlopen(request, timeout=self._timeout) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            message = body.strip() or exc.reason
            raise HttpRequestError(f"HTTP {exc.code} for {request.full_url}: {message}") from exc
        except URLError as exc:
            raise HttpRequestError(f"Request failed for {request.full_url}: {exc.reason}") from exc

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HttpRequestError(f"Invalid JSON returned from {request.full_url}") from exc
