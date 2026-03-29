from __future__ import annotations

import argparse
import json
from pathlib import Path

from weather_bets.application import record_decision_session
from weather_bets.cli import build_parser, main


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "weather-dashboard-cli"
    / "tests"
    / "fixtures"
    / "sample_dashboard.json"
)


def test_help_includes_commands():
    help_text = build_parser().format_help()

    assert "init" in help_text
    assert "sessions" in help_text
    assert "bets" in help_text
    assert "show-session" in help_text
    assert "settle" in help_text
    assert "All commands print JSON." in help_text
    assert "`sessions` returns `db_path` plus `sessions[]`" in help_text
    assert "`show-session` returns the full saved `snapshot` and normalized `bets`." in help_text


def test_subcommand_help_includes_agent_contracts():
    parser = build_parser()
    sessions_help = _format_subcommand_help(parser, "sessions")
    bets_help = _format_subcommand_help(parser, "bets")
    show_session_help = _format_subcommand_help(parser, "show-session")
    settle_help = _format_subcommand_help(parser, "settle")

    assert "selection_count" in sessions_help
    assert "settled_count" in sessions_help
    assert "weather-bets sessions --limit 5" in sessions_help

    assert "Status semantics:" in bets_help
    assert "open     selection has no outcome row yet" in bets_help
    assert "outcome_status" in bets_help
    assert "weather-bets bets --status settled --limit 10" in bets_help

    assert "full saved snapshot" in show_session_help
    assert "`snapshot`, and `bets[]`" in show_session_help

    assert "Settlement status: won, lost, or void." in settle_help
    assert "Observed high temperature, when known." in settle_help
    assert "recorded, not auto-derived." in settle_help
    assert "fully" in settle_help
    assert "paid $1 contract" in settle_help
    assert 'weather-bets settle --bet-id 18 --status void --notes "Market cancelled"' in settle_help


def test_sessions_command_prints_json(tmp_path, capsys):
    db_path = tmp_path / "bets.db"
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    record_decision_session(payload, db_path=db_path, saved_at="2026-03-27T18:15:00+00:00")

    exit_code = main(["sessions", "--db-path", str(db_path), "--limit", "5"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"sessions"' in captured.out
    assert '"selection_count": 2' in captured.out


def _format_subcommand_help(parser, command_name: str) -> str:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices[command_name].format_help()
    raise AssertionError(f"subcommand {command_name} not found")
