from __future__ import annotations

from weather_study_cli.application.forecast_accuracy_spec import (
    evaluate_spec_day_hour,
    include_day_hour_for_censoring,
    predicted_daily_high_f,
    temperature_f_to_int,
)


def test_temperature_f_to_int_rounds() -> None:
    assert temperature_f_to_int(66.4) == 66
    assert temperature_f_to_int(66.6) == 67


def test_censoring_excludes_after_high_observed() -> None:
    tz = "America/Denver"
    ld = "2026-03-26"
    obs = (
        {
            "start": f"{ld}T10:00:00-06:00",
            "temperature_f": 50.0,
        },
        {
            "start": f"{ld}T14:00:00-06:00",
            "temperature_f": 72.0,
        },
    )
    h_int = 72
    assert include_day_hour_for_censoring(obs, local_date=ld, timezone=tz, local_hour=14, h_int=h_int) is True
    assert include_day_hour_for_censoring(obs, local_date=ld, timezone=tz, local_hour=15, h_int=h_int) is False


def test_predicted_high_max_obs_and_remainder() -> None:
    tz = "America/Denver"
    ld = "2026-03-26"
    obs = (
        {"start": f"{ld}T08:00:00-06:00", "temperature_f": 48.0},
        {"start": f"{ld}T13:00:00-06:00", "temperature_f": 65.0},
    )
    fc = (
        {"start": f"{ld}T14:00:00-06:00", "end": f"{ld}T15:00:00-06:00", "temperature_f": 71.0},
        {"start": f"{ld}T15:00:00-06:00", "end": f"{ld}T16:00:00-06:00", "temperature_f": 70.0},
    )
    cap_ts = f"{ld}T14:00:00-06:00"
    p = predicted_daily_high_f(
        obs,
        fc,
        local_date=ld,
        timezone=tz,
        local_hour=14,
        capture_local_timestamp=cap_ts,
    )
    assert p is not None
    assert temperature_f_to_int(p) == 71


def test_evaluate_spec_day_hour_matches() -> None:
    tz = "America/Denver"
    ld = "2026-03-26"
    obs = (
        {"start": f"{ld}T08:00:00-06:00", "temperature_f": 48.0},
        {"start": f"{ld}T14:00:00-06:00", "temperature_f": 72.0},
    )
    fc = (
        {"start": f"{ld}T14:00:00-06:00", "end": f"{ld}T15:00:00-06:00", "temperature_f": 71.0},
        {"start": f"{ld}T15:00:00-06:00", "end": f"{ld}T16:00:00-06:00", "temperature_f": 72.0},
    )
    r = evaluate_spec_day_hour(
        timezone=tz,
        local_date=ld,
        local_hour=14,
        observed_high_temperature_f=72.0,
        observed_payload={"periods": list(obs)},
        local_timestamp=f"{ld}T14:00:00-06:00",
        forecast_rows=fc,
    )
    assert r is True
