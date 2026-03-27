#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CITIES_FILE = REPO_ROOT / "cities.txt"
DEFAULT_OUTPUT_DIR = REPO_ROOT / ".artifacts" / "latest-dashboard"
DEFAULT_SAVE_ENDPOINT = "http://127.0.0.1:8765/record-bets"

CITY_TO_WEATHER_PLACE = {
    "Los Angeles": "Los Angeles,CA",
    "Denver": "Denver,CO",
    "Seattle": "Seattle,WA",
    "Phoenix": "Phoenix,AZ",
    "Las Vegas": "Las Vegas,NV",
    "San Francisco": "San Francisco,CA",
}


class WorkflowError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the repo weather/Kalshi dashboard from installed CLI tools.",
    )
    parser.add_argument(
        "--cities-file",
        default=str(DEFAULT_CITIES_FILE),
        help="Path to the repo-style cities.txt file (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for raw JSON, dashboard.json, and dashboard.html (default: %(default)s)",
    )
    parser.add_argument(
        "--city",
        action="append",
        default=[],
        help="Exact city name from cities.txt. Repeat to limit the build to a subset.",
    )
    parser.add_argument(
        "--save-endpoint",
        default=DEFAULT_SAVE_ENDPOINT,
        help="Save endpoint embedded into dashboard.html (default: %(default)s)",
    )
    return parser


def require_command(name: str) -> None:
    if shutil.which(name):
        return
    raise WorkflowError(f"Required command not found on PATH: {name}")


def load_cities(cities_file: Path) -> list[str]:
    if not cities_file.exists():
        raise WorkflowError(f"Cities file not found: {cities_file}")
    lines = [line.strip() for line in cities_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) % 3 != 0:
        raise WorkflowError(
            f"Expected cities file to contain 3-line blocks (city, Kalshi URL, NOAA URL): {cities_file}"
        )
    cities = [lines[index] for index in range(0, len(lines), 3)]
    unknown = [city for city in cities if city not in CITY_TO_WEATHER_PLACE]
    if unknown:
        raise WorkflowError(
            "Add weather place mappings for unsupported cities before building: "
            + ", ".join(unknown)
        )
    return cities


def select_cities(all_cities: list[str], requested: list[str]) -> list[str]:
    if not requested:
        return all_cities
    unknown = [city for city in requested if city not in all_cities]
    if unknown:
        raise WorkflowError(
            "Requested city is not present in cities.txt: " + ", ".join(unknown)
        )
    selected: list[str] = []
    for city in requested:
        if city not in selected:
            selected.append(city)
    return selected


def run_json_command(command: list[str]) -> dict:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "command failed"
        raise WorkflowError(f"{' '.join(command)} failed: {detail}") from exc
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"{' '.join(command)} returned invalid JSON: {exc.msg}") from exc


def slugify(city: str) -> str:
    return city.lower().replace(" ", "-")


def select_weather_hours(weather_payload: dict) -> tuple[str, list[dict]]:
    now_local = datetime.fromisoformat(weather_payload["range"]["start"])
    local_date = now_local.date().isoformat()
    weather_hours: list[dict] = []
    for period in weather_payload["periods"]:
        start = datetime.fromisoformat(period["start"])
        if start <= now_local:
            continue
        if start.date().isoformat() != local_date:
            continue
        weather_hours.append(
            {
                "start": period["start"],
                "end": period["end"],
                "temperature_f": period["temperature_f"],
                "summary": period["summary"],
                "precipitation_probability_pct": period.get("precipitation_probability_pct"),
                "wind_speed": period.get("wind_speed"),
            }
        )
    return local_date, weather_hours


def build_card(weather_payload: dict, market_payload: dict, weather_hours: list[dict]) -> dict:
    return {
        "city": weather_payload["location"]["city"],
        "state": weather_payload["location"]["state"],
        "timezone": weather_payload["location"]["timezone"],
        "weather_hours": weather_hours,
        "market": {
            "series_title": market_payload["series_title"],
            "event_ticker": market_payload["event_ticker"],
            "event_date_label": market_payload["event_date_label"],
            "rows": [
                {
                    "label": row["label"],
                    "last_price_cents": row.get("last_price_cents"),
                    "yes_bid_cents": row.get("yes_bid_cents"),
                    "yes_ask_cents": row.get("yes_ask_cents"),
                    "no_bid_cents": row.get("no_bid_cents"),
                    "no_ask_cents": row.get("no_ask_cents"),
                    "selected_yes": False,
                    "selected_no": False,
                }
                for row in market_payload["markets"]
            ],
        },
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def render_dashboard_html(dashboard_json: Path, dashboard_html: Path, save_endpoint: str) -> None:
    command = [
        "weather-dashboard",
        "generate-html",
        "--input",
        str(dashboard_json),
        "--output",
        str(dashboard_html),
    ]
    if save_endpoint != DEFAULT_SAVE_ENDPOINT:
        command.extend(["--save-endpoint", save_endpoint])
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "command failed"
        raise WorkflowError(f"{' '.join(command)} failed: {detail}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        require_command("weather")
        require_command("kalshi-weather-markets")
        require_command("weather-dashboard")

        cities_file = Path(args.cities_file).expanduser().resolve()
        output_dir = Path(args.output_dir).expanduser().resolve()
        raw_dir = output_dir / "raw"
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)

        all_cities = load_cities(cities_file)
        selected_cities = select_cities(all_cities, args.city)

        cards: list[dict] = []
        local_dates: list[str] = []

        for city in selected_cities:
            weather_place = CITY_TO_WEATHER_PLACE[city]
            weather_payload = run_json_command(
                ["weather", weather_place, "--range", "next-24h", "--format", "json"]
            )
            market_payload = run_json_command(
                ["kalshi-weather-markets", city, "--format", "json"]
            )

            slug = slugify(city)
            write_json(raw_dir / f"{slug}-weather-next24h.json", weather_payload)
            write_json(raw_dir / f"{slug}-market.json", market_payload)

            local_date, weather_hours = select_weather_hours(weather_payload)
            local_dates.append(local_date)
            cards.append(build_card(weather_payload, market_payload, weather_hours))

        dashboard_payload = {
            "schema_version": "1",
            "dashboard_date": local_dates[0] if local_dates else datetime.now(timezone.utc).date().isoformat(),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cards": cards,
        }

        dashboard_json = output_dir / "dashboard.json"
        dashboard_html = output_dir / "dashboard.html"
        write_json(dashboard_json, dashboard_payload)
        render_dashboard_html(dashboard_json, dashboard_html, args.save_endpoint)

        print(
            json.dumps(
                {
                    "cities": selected_cities,
                    "cities_file": str(cities_file),
                    "dashboard_json": str(dashboard_json),
                    "dashboard_html": str(dashboard_html),
                    "raw_dir": str(raw_dir),
                    "save_endpoint": args.save_endpoint,
                },
                indent=2,
            )
        )
        return 0
    except WorkflowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
