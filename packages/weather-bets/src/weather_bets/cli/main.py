from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from weather_bets.application.journal import (
    initialize_database,
    list_bet_selections,
    list_decision_sessions,
    settle_bet_selection,
    show_decision_session,
)
from weather_bets.domain.errors import WeatherBetsError
from weather_bets.paths import DEFAULT_DB_PATH


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve line breaks for examples in --help output."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather-bets",
        description=(
            "Manage the local SQLite journal for recorded weather bet decisions.\n\n"
            "The journal stores provider-aware decision snapshots plus one normalized row per selected side."
        ),
        epilog=(
            "Agent workflow:\n"
            "  1. `weather-dashboard serve` records provider-aware decision sessions.\n"
            "  2. `weather-bets sessions` lists saved decision events.\n"
            "  3. `weather-bets bets` lists normalized simulated bet rows.\n"
            "  4. `weather-bets show-session <id>` returns the full snapshot plus normalized bets.\n"
            "  5. `weather-bets settle --bet-id <id> ...` manually sets or overrides an outcome.\n\n"
            "Schema policy:\n"
            "  This is a clean-slate local journal. Incompatible older DB versions are not migrated.\n"
            "  Run `weather-bets init --reset` to recreate the database when needed.\n\n"
            "Output contract:\n"
            "  All commands print JSON.\n"
            "  `sessions` returns `db_path` plus `sessions[]`.\n"
            "  `show-session` returns the full saved `snapshot` and normalized `bets`.\n"
            "  Bet rows include provider ids, side, optional stake/entry quote,\n"
            "  and any computed simulator settlement fields."
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser(
        "init",
        help="Create or reset the local SQLite journal.",
        description=(
            "Create the SQLite journal when missing, or reset it from scratch with `--reset`.\n\n"
            "Examples:\n"
            "  weather-bets init\n"
            "  weather-bets init --reset\n"
            "  weather-bets init --db-path /tmp/weather-bets.db --reset"
        ),
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(init)
    init.add_argument(
        "--reset",
        action="store_true",
        help="Delete any existing DB at --db-path and recreate the schema from scratch.",
    )

    sessions = subparsers.add_parser(
        "sessions",
        help="List recorded decision sessions.",
        description=(
            "List recorded decision sessions in reverse chronological id order.\n\n"
            "Output contract:\n"
            "  Returns JSON with `db_path`, `schema_version`, and `sessions[]`.\n"
            "  Each session summary includes `id`, `saved_at`, `dashboard_date`, `generated_at`,\n"
            "  `selection_count`, and `settled_count`.\n\n"
            "Examples:\n"
            "  weather-bets sessions --limit 5\n"
            "  weather-bets sessions --db-path /tmp/weather-bets.db"
        ),
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(sessions)
    _add_limit_argument(sessions)
    _add_format_argument(sessions)

    bets = subparsers.add_parser(
        "bets",
        help="List normalized bet selections.",
        description=(
            "List normalized selected-side rows in reverse chronological id order.\n\n"
            "Status semantics:\n"
            "  open     selection has no outcome row yet\n"
            "  settled  selection has an outcome row, regardless of won/lost/void\n\n"
            "Output contract:\n"
            "  Returns JSON with provider ids, stake fields, entry quote, `outcome_status`,\n"
            "  and optional simulator outputs.\n\n"
            "Examples:\n"
            "  weather-bets bets --status settled --limit 10\n"
            "  weather-bets bets --status open --db-path /tmp/weather-bets.db"
        ),
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(bets)
    _add_limit_argument(bets)
    bets.add_argument("--status", choices=("open", "settled"), help="Optional status filter.")
    _add_format_argument(bets)

    show_session = subparsers.add_parser(
        "show-session",
        help="Show one recorded decision session with its snapshot and selections.",
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(show_session)
    show_session.add_argument("session_id", type=int, help="Decision session id.")
    _add_format_argument(show_session)
    show_session.description = (
        "Show one recorded decision session with its full saved snapshot and normalized bet rows.\n\n"
        "Output contract:\n"
        "  Returns JSON with `db_path`, `schema_version`, `snapshot`, and `bets[]`."
    )

    settle = subparsers.add_parser(
        "settle",
        help="Create or update a manual outcome for one normalized bet selection.",
        description=(
            "Create or update a manual outcome for one normalized bet selection.\n\n"
            "Settlement status: won, lost, or void.\n"
            "Observed high temperature, when known.\n"
            "It is stored as supplemental context.\n"
            "Manual settlement recomputes simulator outputs from the saved stake and entry quote.\n"
            "Gross payout is normally derived from the recorded quote and outcome.\n"
            "It is recorded, not auto-derived.\n"
            "Live provider fills are out of scope.\n"
            "Use `--payout-cents` only when you need to override the gross simulator payout for a\n"
            "fully manual correction. Won rows assume a fully paid $1 contract in the simulator.\n\n"
            "Example:\n"
            '  weather-bets settle --bet-id 18 --status void --notes "Market cancelled"'
        ),
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(settle)
    settle.add_argument("--bet-id", type=int, required=True, help="Bet selection id to settle.")
    settle.add_argument(
        "--status",
        choices=("won", "lost", "void"),
        required=True,
        help="Outcome status: won, lost, or void.",
    )
    settle.add_argument("--resolved-at", help="ISO-8601 timestamp. Defaults to now in UTC.")
    settle.add_argument(
        "--observed-high-temperature-f",
        type=float,
        help="Observed high temperature for the event date when known.",
    )
    settle.add_argument(
        "--payout-cents",
        type=int,
        help="Optional gross payout override in cents.",
    )
    settle.add_argument("--notes", help="Optional settlement notes.")
    _add_format_argument(settle)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_path = Path(args.db_path).expanduser().resolve()

    try:
        if args.command == "init":
            return _print(initialize_database(db_path=db_path, reset=args.reset))
        if args.command == "sessions":
            return _print(list_decision_sessions(db_path=db_path, limit=args.limit))
        if args.command == "bets":
            return _print(list_bet_selections(db_path=db_path, limit=args.limit, status=args.status))
        if args.command == "show-session":
            return _print(show_decision_session(args.session_id, db_path=db_path))
        if args.command == "settle":
            return _print(
                settle_bet_selection(
                    args.bet_id,
                    status=args.status,
                    db_path=db_path,
                    resolved_at=args.resolved_at,
                    observed_high_temperature_f=args.observed_high_temperature_f,
                    payout_cents=args.payout_cents,
                    notes=args.notes,
                )
            )
    except WeatherBetsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


def _add_db_path_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite journal (default: %(default)s)",
    )


def _add_limit_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of rows to return (default: %(default)s)",
    )


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("json",),
        default="json",
        help="Output format (default: %(default)s)",
    )


def _print(payload: dict[str, object]) -> int:
    print(json.dumps(payload, indent=2))
    return 0
