from __future__ import annotations

import argparse
import sys

from weather_bets.domain.errors import WeatherBetsError
from weather_bets.paths import DEFAULT_DB_PATH
from weather_dashboard_cli.application import WeatherDashboardCliError, export_dashboard_html, load_dashboard_snapshot
from weather_dashboard_cli.http.server import DEFAULT_HOST, DEFAULT_PORT, serve_forever


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
            "Serve the local weather decision UI or export it as standalone HTML.\n\n"
            "Agent workflow:\n"
            "  1. Use `weather` to build hourly forecast rows from each city's local current time\n"
            "     through local midnight.\n"
            "  2. Use `kalshi-weather-markets --format json` to fetch the full active market ladder for the\n"
            "     city's current daily event.\n"
            "  3. Normalize those results into the schema documented in\n"
            "     `weather-dashboard serve --help`.\n"
            "  4. Run `weather-dashboard serve --input <dashboard.json>`.\n"
            "  5. Open the local URL, make decisions, and record them into the SQLite journal."
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser(
        "serve",
        help="Serve the local weather decision UI and browser APIs.",
        description=(
            "Serve the local weather decision UI and browser APIs from normalized JSON.\n\n"
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
            "  weather-dashboard serve --input dashboard.json\n"
            "  weather-dashboard serve --input dashboard.json --port 8877\n"
        ),
        formatter_class=HelpFormatter,
    )
    serve.add_argument(
        "--input",
        required=True,
        help="Path to the normalized dashboard JSON that will seed the UI.",
    )
    serve.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Host interface to bind (default: %(default)s)",
    )
    serve.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="TCP port to bind (default: %(default)s)",
    )
    serve.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite journal (default: %(default)s)",
    )

    export_html = subparsers.add_parser(
        "export-html",
        help="Export a standalone HTML document from normalized JSON.",
        description=(
            "Export a standalone HTML document from normalized JSON.\n\n"
            f"{SCHEMA_SNIPPET}\n"
            "Examples:\n"
            "  cat dashboard.json | weather-dashboard export-html > dashboard.html\n"
            "  weather-dashboard export-html --input dashboard.json --output dashboard.html\n"
            "  weather-dashboard export-html --input dashboard.json --save-endpoint "
            "http://127.0.0.1:8765/api/decision-sessions --output dashboard.html"
        ),
        formatter_class=HelpFormatter,
    )
    export_html.add_argument(
        "--input",
        help="Path to a JSON file. Omit to read the normalized payload from stdin.",
    )
    export_html.add_argument(
        "--output",
        help="Path to write the HTML output. Omit to print HTML to stdout.",
    )
    export_html.add_argument(
        "--save-endpoint",
        default=f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/api/decision-sessions",
        help="Absolute save endpoint embedded into the generated dashboard (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "export-html":
            return export_dashboard_html(args.input, args.output, save_endpoint=args.save_endpoint)
        if args.command == "serve":
            try:
                payload = load_dashboard_snapshot(args.input)
                serve_forever(
                    payload=payload,
                    host=args.host,
                    port=args.port,
                    db_path=args.db_path,
                )
            except KeyboardInterrupt:
                return 130
            return 0
    except (WeatherDashboardCliError, WeatherBetsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1
