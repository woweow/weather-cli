from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from weather_bets.domain.errors import WeatherBetsError
from weather_bets.paths import DEFAULT_DB_PATH
from weather_cli.application.errors import WeatherCliError
from weather_bets_sync.application import sync_open_kalshi_bets


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve line breaks for examples in --help output."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather-bets-sync",
        description=(
            "Reconcile unresolved provider-backed journal rows and write settled outcomes back to SQLite."
        ),
        epilog=(
            "Current providers:\n"
            "  kalshi  reads unresolved `provider=kalshi` rows from weather-bets, fetches settled\n"
            "          market results, enriches with NOAA observed highs, and writes outcomes back.\n\n"
            "Examples:\n"
            "  weather-bets-sync kalshi settle-open --dry-run\n"
            "  weather-bets-sync kalshi settle-open --db-path .bets/bets.db\n"
            "  weather-bets-sync kalshi settle-open --bet-id 12 --bet-id 14"
        ),
        formatter_class=HelpFormatter,
    )
    providers = parser.add_subparsers(dest="provider", required=True)
    kalshi = providers.add_parser(
        "kalshi",
        help="Reconcile Kalshi-backed selections.",
        formatter_class=HelpFormatter,
    )
    kalshi_commands = kalshi.add_subparsers(dest="command", required=True)

    settle_open = kalshi_commands.add_parser(
        "settle-open",
        help="Settle unresolved Kalshi rows in the local journal.",
        description=(
            "Read unresolved `provider=kalshi` bet rows, fetch settled event outcomes, and write\n"
            "the resulting win/loss/void plus simulator fields back through weather-bets.\n\n"
            "Settlement rules:\n"
            "  - Kalshi market settlement is authoritative for `won`, `lost`, or `void`.\n"
            "  - Matching is done by exact stored `provider_market_ticker`.\n"
            "  - NOAA observed highs are supplemental enrichment only."
        ),
        formatter_class=HelpFormatter,
    )
    settle_open.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite journal (default: %(default)s)",
    )
    settle_open.add_argument("--dry-run", action="store_true", help="Do not write outcomes; only print the proposed settlement rows.")
    settle_open.add_argument("--limit", type=int, default=100, help="Maximum number of open rows to inspect (default: %(default)s)")
    settle_open.add_argument(
        "--bet-id",
        type=int,
        action="append",
        default=[],
        help="Optional bet selection id filter. Repeat to settle specific rows only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.provider == "kalshi" and args.command == "settle-open":
            payload = sync_open_kalshi_bets(
                db_path=Path(args.db_path).expanduser().resolve(),
                dry_run=args.dry_run,
                limit=args.limit,
                bet_ids=args.bet_id or None,
            )
            print(json.dumps(payload, indent=2))
            return 0
    except (WeatherBetsError, WeatherCliError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1
