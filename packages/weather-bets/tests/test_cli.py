from __future__ import annotations

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


def test_sessions_command_prints_json(tmp_path, capsys):
    db_path = tmp_path / "bets.db"
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    record_decision_session(payload, db_path=db_path, saved_at="2026-03-27T18:15:00+00:00")

    exit_code = main(["sessions", "--db-path", str(db_path), "--limit", "5"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"sessions"' in captured.out
    assert '"selection_count": 2' in captured.out

