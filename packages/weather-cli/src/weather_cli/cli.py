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
from weather_cli.station_presets import format_station_presets_for_help


DEFAULT_CONTACT_EMAIL = "weather-cli@example.com"


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve line breaks for examples in --help output."""


def build_parser() -> argparse.ArgumentParser:
    station_presets = format_station_presets_for_help()
    parser = argparse.ArgumentParser(
        prog="weather",
        description=(
            "Query NOAA weather.gov observations and hourly forecasts for a strict city,state place.\n\n"
            "Settlement-aligned station presets:\n"
            f"{station_presets}"
        ),
        epilog=(
            "Range semantics:\n"
            "  Observation ranges:\n"
            "    yesterday    Previous local calendar day (00:00 to 23:59:59)\n"
            "    today        Observations so far since local midnight\n"
            "    previous-24h Rolling observation window from now minus 24 hours\n"
            "  Forecast range:\n"
            "    next-24h     Rolling 24-hour hourly forecast from now\n\n"
            "Examples:\n"
            "  weather \"Seattle,WA\" --range today\n"
            "  weather \"Seattle,WA\" --range next-24h\n"
            "  weather \"Los Angeles,CA\" --range yesterday --format table\n"
            "  weather \"Los Angeles,CA\" --range yesterday --nearest-station\n"
            "  weather \"Seattle,WA\" --range yesterday --station KBFI\n"
            "  weather \"Denver,CO\" --range today\n"
            "  weather \"San Francisco,CA\" --range yesterday"
        ),
        formatter_class=HelpFormatter,
    )
    parser.add_argument(
        "place",
        help='Strict city,state input such as "Seattle,WA" or "Los Angeles,CA"',
    )
    parser.add_argument(
        "--range",
        required=True,
        choices=VALID_RANGES,
        help=(
            "Time window to query. Observation ranges: yesterday, today, previous-24h. "
            "Forecast range: next-24h."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("json", "table"),
        default="json",
        help="Output format for the normalized result (default: json)",
    )
    parser.add_argument(
        "--station",
        help="Force a NOAA station ID for observation or forecast anchoring, e.g. KSEA or KLAX",
    )
    parser.add_argument(
        "--nearest-station",
        action="store_true",
        help="Ignore built-in city presets. Observations use the nearest station with data; forecasts use the resolved city point.",
    )
    parser.add_argument(
        "--contact-email",
        default=os.getenv("WEATHER_CLI_CONTACT_EMAIL", DEFAULT_CONTACT_EMAIL),
        help="Contact email embedded in the NOAA User-Agent header required by NOAA",
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
