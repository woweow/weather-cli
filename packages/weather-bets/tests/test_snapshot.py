from __future__ import annotations

import json
from pathlib import Path

import pytest

from weather_bets.domain.errors import SnapshotValidationError
from weather_bets.domain.simulator import simulate_pnl
from weather_bets.domain.snapshot import extract_selected_bets, normalize_dashboard_snapshot


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "weather-dashboard-cli"
    / "tests"
    / "fixtures"
    / "sample_dashboard.json"
)


def test_normalize_dashboard_snapshot_sets_default_selection_state():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del payload["cards"][0]["market"]["rows"][0]["selected_yes"]
    del payload["cards"][0]["market"]["rows"][0]["selected_no"]

    normalized = normalize_dashboard_snapshot(payload)

    row = normalized["cards"][0]["market"]["rows"][0]
    assert row["selected_yes"] is False
    assert row["selected_no"] is False


def test_normalize_dashboard_snapshot_normalizes_usd_stake_strings():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["cards"][0]["market"]["rows"][1]["yes_stake_usd"] = "12.5"

    normalized = normalize_dashboard_snapshot(payload)

    assert normalized["cards"][0]["market"]["rows"][1]["yes_stake_usd"] == "12.50"


def test_normalize_dashboard_snapshot_rejects_invalid_shape():
    with pytest.raises(SnapshotValidationError):
        normalize_dashboard_snapshot({"dashboard_date": "2026-03-27", "cards": []})


def test_extract_selected_bets_emits_one_row_per_side_with_provider_identity():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["cards"][0]["market"]["rows"][0]["selected_yes"] = True
    payload["cards"][0]["market"]["rows"][0]["selected_no"] = True

    selections = extract_selected_bets(normalize_dashboard_snapshot(payload))

    first_row_sides = [
        selection["side"]
        for selection in selections
        if selection["card_index"] == 0 and selection["row_index"] == 0
    ]
    assert first_row_sides == ["yes", "no"]
    assert selections[0]["provider"] == "kalshi"
    assert selections[0]["provider_market_ticker"].startswith("KXHIGHTSEA-26MAR26")


def test_simulate_pnl_uses_decimal_contract_math():
    result = simulate_pnl(stake_cents=1250, entry_price_cents=45, outcome_status="won")

    assert result["simulated_contract_count"] == "27.7778"
    assert result["simulated_gross_payout_cents"] == 2778
    assert result["simulated_net_pnl_cents"] == 1528
