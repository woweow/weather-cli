from __future__ import annotations

import argparse
import io
from pathlib import Path

from weather_dashboard_cli.cli import build_parser, main


FIXTURE = Path(__file__).parent / "fixtures" / "sample_dashboard.json"


def test_help_includes_commands_and_schema():
    help_text = build_parser().format_help()

    assert "export-html" in help_text
    assert "serve" in help_text
    assert "local current time" in help_text
    assert "SQLite journal" in help_text or "SQLite" in help_text
    assert "`serve` hosts the local UI and writes decision sessions into the SQLite journal." in help_text
    assert "Inspect or settle those rows with `weather-bets`." in help_text
    assert "weather-bets-sync kalshi settle-open" in help_text


def test_subcommand_help_includes_routes_and_save_behavior():
    parser = build_parser()
    serve_help = _format_subcommand_help(parser, "serve")
    export_help = _format_subcommand_help(parser, "export-html")

    assert "Server routes:" in serve_help
    assert "POST /api/decision-sessions" in serve_help
    assert "`saved_at`, `session_id`, `selection_count`, and `db_path`." in serve_help
    assert "weather-dashboard serve --input dashboard.json --db-path /tmp/weather-bets.db" in serve_help

    assert "does not start a server or create a database" in export_help
    assert "If nothing is listening at that endpoint, the UI will render but saving will fail." in export_help
    assert "weather-dashboard export-html --input dashboard.json --output dashboard.html" in export_help


def test_export_html_writes_output_file():
    fixture = FIXTURE
    output_path = fixture.parent / "generated-dashboard.html"
    try:
        exit_code = main(
            [
                "export-html",
                "--input",
                str(fixture),
                "--output",
                str(output_path),
            ]
        )
        assert exit_code == 0
        rendered = output_path.read_text(encoding="utf-8")
        assert "Record predictions" in rendered
        assert "Seattle" in rendered
        assert '"last_price_cents": 44' in rendered
        assert '"provider_market_ticker": "KXHIGHTSEA-26MAR26-B53.5"' in rendered
        assert "No last price" in rendered
    finally:
        if output_path.exists():
            output_path.unlink()


def test_export_html_reads_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(FIXTURE.read_text(encoding="utf-8")))
    exit_code = main(["export-html"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Weather and Kalshi bet board" in captured.out
    assert '"city": "Seattle"' in captured.out


def _format_subcommand_help(parser, command_name: str) -> str:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices[command_name].format_help()
    raise AssertionError(f"subcommand {command_name} not found")
