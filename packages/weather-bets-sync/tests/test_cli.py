from weather_bets_sync.cli import build_parser


def test_help_includes_kalshi_settle_open_examples():
    help_text = build_parser().format_help()

    assert "kalshi" in help_text
    assert "settle-open" in help_text
    assert "weather-bets-sync kalshi settle-open --dry-run" in help_text
