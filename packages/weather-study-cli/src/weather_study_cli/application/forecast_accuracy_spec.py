from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import Any

from zoneinfo import ZoneInfo

from weather_study_cli.application.market_utils import find_winning_market_row


def temperature_f_to_int(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def parse_local_datetime(iso_text: str, timezone: str) -> datetime:
    raw = datetime.fromisoformat(iso_text.replace("Z", "+00:00"))
    if raw.tzinfo is None:
        return raw.replace(tzinfo=ZoneInfo(timezone))
    return raw.astimezone(ZoneInfo(timezone))


def local_date_string(dt: datetime) -> str:
    return dt.date().isoformat()


def local_day_bounds(local_date: str, timezone: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    d = date.fromisoformat(local_date)
    start = datetime.combine(d, time.min, tzinfo=zone)
    end = datetime.combine(d + timedelta(days=1), time.min, tzinfo=zone)
    return start, end


def max_observed_temp_strictly_before_local_hour(
    observation_periods: tuple[dict[str, Any], ...],
    *,
    local_date: str,
    timezone: str,
    exclusive_local_hour: int,
) -> float | None:
    zone = ZoneInfo(timezone)
    target = date.fromisoformat(local_date)
    best: float | None = None
    for period in observation_periods:
        temp = period.get("temperature_f")
        if temp is None:
            continue
        start_s = period.get("start")
        if not start_s:
            continue
        dt = parse_local_datetime(str(start_s), timezone)
        if dt.date() != target:
            continue
        if dt.hour < exclusive_local_hour:
            t = float(temp)
            if best is None or t > best:
                best = t
    return best


def max_observed_temp_through_local_hour(
    observation_periods: tuple[dict[str, Any], ...],
    *,
    local_date: str,
    timezone: str,
    inclusive_local_hour: int,
) -> float | None:
    target = date.fromisoformat(local_date)
    best: float | None = None
    for period in observation_periods:
        temp = period.get("temperature_f")
        if temp is None:
            continue
        start_s = period.get("start")
        if not start_s:
            continue
        dt = parse_local_datetime(str(start_s), timezone)
        if dt.date() != target:
            continue
        if dt.hour <= inclusive_local_hour:
            t = float(temp)
            if best is None or t > best:
                best = t
    return best


def max_forecast_temp_remainder_of_local_day(
    forecast_rows: tuple[dict[str, Any], ...],
    *,
    capture_local: datetime,
    local_date: str,
    timezone: str,
) -> float | None:
    _, day_end = local_day_bounds(local_date, timezone)
    best: float | None = None
    for row in forecast_rows:
        temp = row.get("temperature_f")
        if temp is None:
            continue
        start_s = row.get("start")
        end_s = row.get("end")
        if not start_s or not end_s:
            continue
        p_start = parse_local_datetime(str(start_s), timezone)
        p_end = parse_local_datetime(str(end_s), timezone)
        if p_end <= capture_local or p_start >= day_end:
            continue
        if p_end <= capture_local:
            continue
        overlap_start = max(p_start, capture_local)
        if overlap_start >= day_end:
            continue
        t = float(temp)
        if best is None or t > best:
            best = t
    return best


def include_day_hour_for_censoring(
    observation_periods: tuple[dict[str, Any], ...],
    *,
    local_date: str,
    timezone: str,
    local_hour: int,
    h_int: int,
) -> bool:
    m_before = max_observed_temp_strictly_before_local_hour(
        observation_periods,
        local_date=local_date,
        timezone=timezone,
        exclusive_local_hour=local_hour,
    )
    if m_before is None:
        return True
    return temperature_f_to_int(m_before) < h_int


def predicted_daily_high_f(
    observation_periods: tuple[dict[str, Any], ...],
    forecast_rows: tuple[dict[str, Any], ...],
    *,
    local_date: str,
    timezone: str,
    local_hour: int,
    capture_local_timestamp: str,
) -> float | None:
    m_obs = max_observed_temp_through_local_hour(
        observation_periods,
        local_date=local_date,
        timezone=timezone,
        inclusive_local_hour=local_hour,
    )
    cap = parse_local_datetime(capture_local_timestamp, timezone)
    m_fcst = max_forecast_temp_remainder_of_local_day(
        forecast_rows,
        capture_local=cap,
        local_date=local_date,
        timezone=timezone,
    )
    if m_obs is None and m_fcst is None:
        return None
    candidates = [x for x in (m_obs, m_fcst) if x is not None]
    if not candidates:
        return None
    return max(candidates)


def observation_periods_from_payload(observed_payload: dict[str, Any] | None) -> tuple[dict[str, Any], ...]:
    if not observed_payload:
        return ()
    periods = observed_payload.get("periods")
    if not isinstance(periods, list):
        return ()
    return tuple(p for p in periods if isinstance(p, dict))


def evaluate_spec_day_hour(
    *,
    timezone: str,
    local_date: str,
    local_hour: int,
    observed_high_temperature_f: float | None,
    observed_payload: dict[str, Any] | None,
    local_timestamp: str,
    forecast_rows: tuple[dict[str, Any], ...],
) -> bool | None:
    """Return True if predicted daily high matches H, False if eligible but wrong, None if excluded."""
    if observed_high_temperature_f is None:
        return None
    h_int = temperature_f_to_int(float(observed_high_temperature_f))
    if h_int is None:
        return None
    obs_periods = observation_periods_from_payload(observed_payload)
    if not obs_periods:
        return None
    if not include_day_hour_for_censoring(
        obs_periods,
        local_date=local_date,
        timezone=timezone,
        local_hour=local_hour,
        h_int=h_int,
    ):
        return None
    p_high = predicted_daily_high_f(
        obs_periods,
        forecast_rows,
        local_date=local_date,
        timezone=timezone,
        local_hour=local_hour,
        capture_local_timestamp=local_timestamp,
    )
    if p_high is None:
        return None
    p_int = temperature_f_to_int(p_high)
    if p_int is None:
        return None
    return p_int == h_int


def spec_day_hour_metrics_bundle(
    *,
    timezone: str,
    local_date: str,
    local_hour: int,
    observed_high_temperature_f: float | None,
    observed_payload: dict[str, Any] | None,
    local_timestamp: str,
    forecast_rows: tuple[dict[str, Any], ...],
    capture_json: str,
) -> tuple[bool, bool | None, int | None]:
    """Returns (eligible_for_spec_metrics, correct_if_eligible, winning_last_price_cents_if_eligible)."""
    eval_result = evaluate_spec_day_hour(
        timezone=timezone,
        local_date=local_date,
        local_hour=local_hour,
        observed_high_temperature_f=observed_high_temperature_f,
        observed_payload=observed_payload,
        local_timestamp=local_timestamp,
        forecast_rows=forecast_rows,
    )
    if eval_result is None:
        return False, None, None
    try:
        payload = json.loads(capture_json)
    except json.JSONDecodeError:
        return False, None, None
    market_payload = payload.get("market", {}).get("payload")
    market_rows = tuple(market_payload.get("markets", [])) if market_payload else ()
    if not market_rows:
        return False, None, None
    if observed_high_temperature_f is None:
        return False, None, None
    winning = find_winning_market_row(market_rows, float(observed_high_temperature_f))
    if winning is None:
        return False, None, None
    price = winning.get("last_price_cents")
    if price is None:
        return False, None, None
    return True, eval_result, int(price)
