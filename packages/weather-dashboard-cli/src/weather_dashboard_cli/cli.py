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
              "chance_display": "41%",
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
        description="Generate weather and Kalshi dashboard HTML or run the local bet recorder.",
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
            "  - `chance_display` is optional and should come directly from upstream data.\n"
            "  - `selected_yes` and `selected_no` are optional, independent booleans.\n"
            "  - Input may include extra metadata fields; the renderer ignores what it does not need."
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
            "/Users/brianrogers/coding/weather-cli/.bets/DD_MM_YYYY_bets_placed.json.\n"
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
