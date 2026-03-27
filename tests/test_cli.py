from weather_cli.cli import build_parser


def test_help_includes_examples_and_presets():
    help_text = build_parser().format_help()

    assert "Los Angeles,CA -> KLAX" in help_text
    assert "Seattle,WA     -> KSEA" in help_text
    assert 'weather "Seattle,WA" --range today' in help_text
    assert "Range semantics:" in help_text
