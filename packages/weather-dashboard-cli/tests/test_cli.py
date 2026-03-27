from __future__ import annotations

import io
from pathlib import Path

from weather_dashboard_cli.cli import build_parser, main


FIXTURE = Path(__file__).parent / "fixtures" / "sample_dashboard.json"


def test_help_includes_commands_and_schema():
    help_text = build_parser().format_help()

    assert "generate-html" in help_text
    assert "serve-bets" in help_text
    assert "local current time" in help_text
    assert "Record bets" in help_text


def test_generate_html_writes_output_file():
    fixture = FIXTURE
    output_path = fixture.parent / "generated-dashboard.html"
    try:
        exit_code = main(
            [
                "generate-html",
                "--input",
                str(fixture),
                "--output",
                str(output_path),
            ]
        )
        assert exit_code == 0
        rendered = output_path.read_text(encoding="utf-8")
        assert "Record bets" in rendered
        assert "Seattle" in rendered
        assert '"last_price_cents": 46' in rendered
        assert "No last price" in rendered
    finally:
        if output_path.exists():
            output_path.unlink()


def test_generate_html_reads_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(FIXTURE.read_text(encoding="utf-8")))
    exit_code = main(["generate-html"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Weather and Kalshi bet board" in captured.out
    assert '"city": "Seattle"' in captured.out
