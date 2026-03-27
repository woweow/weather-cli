from __future__ import annotations

import argparse
import sys
from pathlib import Path

from weather_dashboard_cli.errors import WeatherDashboardCliError
from weather_dashboard_cli.html import render_dashboard_html
from weather_dashboard_cli.payload import load_dashboard_payload
from weather_dashboard_cli.server import DEFAULT_HOST, DEFAULT_PORT, serve_forever


SCHEMA_SNIPPET = """Input schema:
  {
    "schema_version": "1",
    "dashboard_date": "2026-03-27",
    "generated_at": "2026-03-27T14:02:00Z",
    "cards": [
      {
        "city": "Seattle",
        "state": "WA",
        "timezone": "America/Los_Angeles",
        "weather_hours": [
          {
            "start": "2026-03-27T07:00:00-07:00",
            "end": "2026-03-27T08:00:00-07:00",
            "temperature_f": 39,
            "summary": "Partly Sunny",
            "precipitation_probability_pct": 0,
            "wind_speed": "2 mph"
          }
        ],
        "market": {
          "series_title": "Seattle Maximum Temperature Daily",
          "event_ticker": "KXHIGHTSEA-26MAR27",
          "event_date_label": "Mar 27, 2026",
          "rows": [
            {
              "label": "55°F to 56°F",
              "last_price_cents": 46,
              "yes_bid_cents": 45,
              "yes_ask_cents": 46,
              "no_bid_cents": 54,
              "no_ask_cents": 57,
              "selected_yes": false,
              "selected_no": false
            }
          ]
        }
      }
    ]
  }
"""


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve line breaks for schema examples."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather-dashboard",
        description=(
            "Generate weather and Kalshi dashboard HTML or run the local bet recorder.\n\n"
            "Agent workflow:\n"
            "  1. Use `weather` to build hourly forecast rows from each city's local current time\n"
            "     through local midnight.\n"
            "  2. Use `kalshi-weather-markets --format json` to fetch the full active market ladder for the\n"
            "     city's current daily event.\n"
            "  3. Normalize those results into the schema documented in\n"
            "     `weather-dashboard generate-html --help`.\n"
            "  4. Run `weather-dashboard generate-html`.\n"
            "  5. Run `weather-dashboard serve-bets` before opening the HTML if you want the\n"
            "     Record bets button to save data."
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_html = subparsers.add_parser(
        "generate-html",
        help="Generate a self-contained dashboard HTML document from normalized JSON.",
        description=(
            "Generate a self-contained dashboard HTML document from normalized JSON.\n\n"
            f"{SCHEMA_SNIPPET}\n"
            "Notes:\n"
            "  - `weather_hours` must be hourly forecast rows from the city's local current time\n"
            "    through local midnight, in Fahrenheit.\n"
            "  - `market.rows` must contain the full active ladder for the selected daily event,\n"
            "    not a filtered subset.\n"
            "  - `last_price_cents` is the primary headline market value shown on each row.\n"
            "  - `selected_yes` and `selected_no` are optional, independent booleans.\n"
            "  - Input may include extra metadata fields; the renderer ignores what it does not need.\n\n"
            "Examples:\n"
            "  cat dashboard.json | weather-dashboard generate-html > dashboard.html\n"
            "  weather-dashboard generate-html --input dashboard.json --output dashboard.html\n"
            "  weather-dashboard generate-html --input dashboard.json --save-endpoint "
            "http://127.0.0.1:8765/record-bets --output dashboard.html"
        ),
        formatter_class=HelpFormatter,
    )
    generate_html.add_argument(
        "--input",
        help="Path to a JSON file. Omit to read the normalized payload from stdin.",
    )
    generate_html.add_argument(
        "--output",
        help="Path to write the HTML output. Omit to print HTML to stdout.",
    )
    generate_html.add_argument(
        "--save-endpoint",
        default=f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/record-bets",
        help="Absolute save endpoint embedded into the generated dashboard (default: %(default)s)",
    )

    serve_bets = subparsers.add_parser(
        "serve-bets",
        help="Run the local bet-recording HTTP endpoint.",
        description=(
            "Run the local bet-recording HTTP endpoint.\n\n"
            "The server accepts POST /record-bets and appends snapshots to the fixed repo path\n"
            "/Users/brianrogers/coding/weather-cli/.bets/DD_MM_YYYY_bets_placed.json.\n\n"
            "Run this command before opening generated dashboard HTML if you want the Record bets\n"
            "button to persist selections.\n"
        ),
        formatter_class=HelpFormatter,
    )
    serve_bets.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Host interface to bind (default: %(default)s)",
    )
    serve_bets.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="TCP port to bind (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "generate-html":
            return _generate_html(args.input, args.output, args.save_endpoint)
        if args.command == "serve-bets":
            try:
                serve_forever(args.host, args.port)
            except KeyboardInterrupt:
                return 130
            return 0
    except WeatherDashboardCliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


def _generate_html(input_path: str | None, output_path: str | None, save_endpoint: str) -> int:
    payload = load_dashboard_payload(input_path)
    html = render_dashboard_html(payload, save_endpoint=save_endpoint)
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
    else:
        sys.stdout.write(html)
    return 0
