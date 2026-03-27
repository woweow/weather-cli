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
            "The journal stores each decision-session snapshot plus one normalized row per selected side."
        ),
        formatter_class=HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser(
        "init",
        help="Create or upgrade the local SQLite journal.",
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(init)

    sessions = subparsers.add_parser(
        "sessions",
        help="List recorded decision sessions.",
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(sessions)
    _add_limit_argument(sessions)
    _add_format_argument(sessions)

    bets = subparsers.add_parser(
        "bets",
        help="List normalized bet selections.",
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(bets)
    _add_limit_argument(bets)
    bets.add_argument(
        "--status",
        choices=("open", "settled"),
        help="Optional status filter.",
    )
    _add_format_argument(bets)

    show_session = subparsers.add_parser(
        "show-session",
        help="Show one recorded decision session with its snapshot and selections.",
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(show_session)
    show_session.add_argument("session_id", type=int, help="Decision session id.")
    _add_format_argument(show_session)

    settle = subparsers.add_parser(
        "settle",
        help="Create or update a manual outcome for one normalized bet selection.",
        formatter_class=HelpFormatter,
    )
    _add_db_path_argument(settle)
    settle.add_argument("--bet-id", type=int, required=True, help="Bet selection id to settle.")
    settle.add_argument("--status", choices=("won", "lost", "void"), required=True, help="Settlement status.")
    settle.add_argument("--resolved-at", help="ISO-8601 timestamp. Defaults to now in UTC.")
    settle.add_argument("--actual-temperature-f", type=float, help="Observed high temperature, when known.")
    settle.add_argument("--payout-cents", type=int, help="Manual payout amount in cents.")
    settle.add_argument("--notes", help="Optional settlement notes.")
    _add_format_argument(settle)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_path = Path(args.db_path).expanduser().resolve()

    try:
        if args.command == "init":
            return _print(initialize_database(db_path=db_path), args)
        if args.command == "sessions":
            return _print(list_decision_sessions(db_path=db_path, limit=args.limit), args)
        if args.command == "bets":
            return _print(
                list_bet_selections(db_path=db_path, limit=args.limit, status=args.status),
                args,
            )
        if args.command == "show-session":
            return _print(show_decision_session(args.session_id, db_path=db_path), args)
        if args.command == "settle":
            return _print(
                settle_bet_selection(
                    args.bet_id,
                    status=args.status,
                    db_path=db_path,
                    resolved_at=args.resolved_at,
                    actual_temperature_f=args.actual_temperature_f,
                    payout_cents=args.payout_cents,
                    notes=args.notes,
                ),
                args,
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


def _print(payload: dict, args: argparse.Namespace) -> int:
    print(json.dumps(payload, indent=2))
    return 0
