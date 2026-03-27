from __future__ import annotations

import argparse
import os
import sys

from weather_cli.errors import WeatherCliError
from weather_cli.formatting import render_output
from weather_cli.geocoding import OpenMeteoGeocoder
from weather_cli.http import JsonHttpClient
from weather_cli.noaa import NoaaApi
from weather_cli.ranges import VALID_RANGES
from weather_cli.service import WeatherService


DEFAULT_CONTACT_EMAIL = "weather-cli@example.com"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather",
        description="Query NOAA weather.gov yesterday/today and +/-24h weather for a city,state place.",
    )
    parser.add_argument("place", help='Strict city,state input such as "Seattle,WA"')
    parser.add_argument("--range", required=True, choices=VALID_RANGES, help="Requested weather window")
    parser.add_argument("--format", choices=("json", "table"), default="json", help="Output format")
    parser.add_argument("--station", help="Optional NOAA station override, e.g. KSEA")
    parser.add_argument(
        "--nearest-station",
        action="store_true",
        help="Ignore built-in city presets and use the nearest station with data",
    )
    parser.add_argument(
        "--contact-email",
        default=os.getenv("WEATHER_CLI_CONTACT_EMAIL", DEFAULT_CONTACT_EMAIL),
        help="Contact email embedded in the NOAA User-Agent header",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    user_agent = f"weather-cli/0.1 ({args.contact_email})"
    service = WeatherService(
        geocoder=OpenMeteoGeocoder(JsonHttpClient(user_agent=user_agent)),
        noaa_api=NoaaApi(JsonHttpClient(user_agent=user_agent)),
    )

    try:
        payload = service.fetch(
            args.place,
            args.range,
            station_override=args.station,
            use_station_presets=not args.nearest_station,
        )
    except WeatherCliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(render_output(payload, args.format))
    return 0
