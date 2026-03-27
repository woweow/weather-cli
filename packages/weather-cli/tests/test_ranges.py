from datetime import datetime
from zoneinfo import ZoneInfo

from weather_cli.application.ranges import resolve_time_window


def test_yesterday_uses_full_previous_local_day():
    now = datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC"))
    window = resolve_time_window("yesterday", "America/Los_Angeles", now=now)

    assert window.start.isoformat() == "2026-03-25T00:00:00-07:00"
    assert window.end.isoformat() == "2026-03-26T00:00:00-07:00"
    assert window.mode == "observations"


def test_today_ends_at_now_in_local_timezone():
    now = datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC"))
    window = resolve_time_window("today", "America/Los_Angeles", now=now)

    assert window.start.isoformat() == "2026-03-26T00:00:00-07:00"
    assert window.end.isoformat() == "2026-03-26T12:30:00-07:00"


def test_previous_24h_is_rolling_window():
    now = datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC"))
    window = resolve_time_window("previous-24h", "America/Los_Angeles", now=now)

    assert window.start.isoformat() == "2026-03-25T12:30:00-07:00"
    assert window.end.isoformat() == "2026-03-26T12:30:00-07:00"


def test_next_24h_switches_to_forecast_mode():
    now = datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC"))
    window = resolve_time_window("next-24h", "America/Los_Angeles", now=now)

    assert window.start.isoformat() == "2026-03-26T12:30:00-07:00"
    assert window.end.isoformat() == "2026-03-27T12:30:00-07:00"
    assert window.mode == "forecast"


def test_rest_of_today_stops_at_next_local_midnight():
    now = datetime(2026, 3, 26, 19, 30, tzinfo=ZoneInfo("UTC"))
    window = resolve_time_window("rest-of-today", "America/Los_Angeles", now=now)

    assert window.start.isoformat() == "2026-03-26T12:30:00-07:00"
    assert window.end.isoformat() == "2026-03-27T00:00:00-07:00"
    assert window.mode == "forecast"
