from weather_cli.cli import build_parser


def test_help_includes_examples_and_presets():
    help_text = build_parser().format_help()

    assert "Denver,CO        -> KDEN" in help_text
    assert "Las Vegas,NV     -> KLAS" in help_text
    assert "Los Angeles,CA   -> KLAX" in help_text
    assert "Phoenix,AZ       -> KPHX" in help_text
    assert "San Francisco,CA -> KSFO" in help_text
    assert "Seattle,WA       -> KSEA" in help_text
    assert 'weather "Seattle,WA" --range today' in help_text
    assert 'weather "Seattle,WA" --range next-24h' in help_text
    assert 'weather "Denver,CO" --range today' in help_text
    assert "Range semantics:" in help_text
    assert "Observation ranges:" in help_text
    assert "Forecast range:" in help_text
    assert "today        Observations so far since local midnight" in help_text
    assert "next-24h     Rolling 24-hour hourly forecast from now" in help_text
