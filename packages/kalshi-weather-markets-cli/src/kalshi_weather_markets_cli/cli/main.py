from __future__ import annotations

import argparse
import sys

from kalshi_weather_markets_cli.adapters.client import KalshiPublicClient
from kalshi_weather_markets_cli.application.catalog import documented_cities_help_text
from kalshi_weather_markets_cli.application.errors import KalshiWeatherCliError
from kalshi_weather_markets_cli.application.service import KalshiWeatherService
from kalshi_weather_markets_cli.cli.formatting import render_json, render_text


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve line breaks for examples in --help output."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kalshi-weather-markets",
        description=(
            "Inspect Kalshi daily high-temperature market ladders for a supported city.\n\n"
            "This CLI uses Kalshi's public market-data endpoints and does not require API keys."
        ),
        epilog=(
            "City input:\n"
            "  Exact-name based in v1. Use --list-cities for the live supported list.\n"
            "  Quote multi-word names in the shell, for example \"Los Angeles\".\n\n"
            "Selection behavior:\n"
            "  The CLI fetches the city's open market ladder and picks the active event with the\n"
            "  earliest close time, which is usually the current trading day when multiple days\n"
            "  are open.\n\n"
            "Normalized market contract:\n"
            "  The JSON payload contains the full active ladder for the selected daily event,\n"
            "  sorted by temperature range. Each row includes `label`, `last_price_cents`,\n"
            "  `yes_bid_cents`, `yes_ask_cents`, `no_bid_cents`, and `no_ask_cents`.\n"
            "  This shape is suitable for agents building weather-dashboard input.\n\n"
            "Output:\n"
            "  text  Series and event header, then ladder rows with range, yes bid/ask,\n"
            "        no bid/ask, and raw last price.\n"
            "  json  Normalized snapshot payload for scripting.\n\n"
            "Supported exact city names:\n"
            f"  {documented_cities_help_text()}\n\n"
            "Examples:\n"
            "  kalshi-weather-markets Seattle\n"
            "  kalshi-weather-markets \"Los Angeles\"\n"
            "  kalshi-weather-markets --list-cities\n"
            "  kalshi-weather-markets Seattle --format json\n"
            "  kalshi-weather-markets Seattle --format json > seattle-market.json\n\n"
            "Errors:\n"
            "  Prints a message to stderr and exits non-zero on unsupported cities or API failures."
        ),
        formatter_class=HelpFormatter,
    )
    parser.add_argument(
        "city",
        nargs="?",
        help='Exact city name such as "Seattle" or "Los Angeles"',
    )
    parser.add_argument(
        "--list-cities",
        action="store_true",
        help="List supported exact city names and exit",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the market snapshot (default: text)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = KalshiWeatherService(client=KalshiPublicClient())

    if args.list_cities:
        print("\n".join(service.list_supported_cities()))
        return 0

    if not args.city:
        parser.error("the following arguments are required: city")

    try:
        snapshot = service.fetch_city_ladder(args.city)
    except KalshiWeatherCliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(render_json(snapshot))
    else:
        print(render_text(snapshot))
    return 0
