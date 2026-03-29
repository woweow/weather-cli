from __future__ import annotations

import json
from pathlib import Path

from weather_bets.application import (
    initialize_database,
    list_bet_selections,
    list_decision_sessions,
    record_decision_session,
    resolve_bet_selection,
    settle_bet_selection,
    show_decision_session,
)


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "weather-dashboard-cli"
    / "tests"
    / "fixtures"
    / "sample_dashboard.json"
)


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_record_decision_session_persists_provider_rows_and_snapshot(tmp_path):
    db_path = tmp_path / "bets.db"

    result = record_decision_session(load_fixture(), db_path=db_path, saved_at="2026-03-27T18:00:00+00:00")
    session = show_decision_session(result["id"], db_path=db_path)

    assert result["selection_count"] == 2
    assert session["snapshot"]["schema_version"] == "2"
    assert [bet["side"] for bet in session["bets"]] == ["yes", "no"]
    assert session["bets"][0]["provider_market_ticker"] == "KXHIGHTSEA-26MAR26-B53.5"
    assert session["bets"][0]["stake_cents"] == 1250
    assert session["bets"][0]["entry_price_cents"] == 45


def test_record_decision_session_allows_zero_selected_rows(tmp_path):
    db_path = tmp_path / "bets.db"
    payload = load_fixture()
    for card in payload["cards"]:
        for row in card["market"]["rows"]:
            row["selected_yes"] = False
            row["selected_no"] = False

    result = record_decision_session(payload, db_path=db_path, saved_at="2026-03-27T18:05:00+00:00")
    sessions = list_decision_sessions(db_path=db_path)
    bets = list_bet_selections(db_path=db_path)

    assert result["selection_count"] == 0
    assert len(sessions["sessions"]) == 1
    assert bets["bets"] == []


def test_settle_bet_selection_updates_simulator_fields(tmp_path):
    db_path = tmp_path / "bets.db"
    result = record_decision_session(load_fixture(), db_path=db_path, saved_at="2026-03-27T18:10:00+00:00")
    bet_id = show_decision_session(result["id"], db_path=db_path)["bets"][0]["id"]

    settled = settle_bet_selection(
        bet_id,
        status="won",
        db_path=db_path,
        resolved_at="2026-03-28T09:00:00+00:00",
        observed_high_temperature_f=52.0,
        notes="Manual settlement",
    )

    bets = list_bet_selections(db_path=db_path, status="settled")
    assert settled["bet"]["outcome_status"] == "won"
    assert settled["bet"]["simulated_gross_payout_cents"] == 2778
    assert settled["bet"]["simulated_net_pnl_cents"] == 1528
    assert bets["bets"][0]["observed_high_temperature_f"] == 52.0


def test_resolve_bet_selection_writes_provider_fields(tmp_path):
    db_path = tmp_path / "bets.db"
    initialize_database(db_path=db_path, reset=True)
    result = record_decision_session(load_fixture(), db_path=db_path, saved_at="2026-03-27T18:15:00+00:00")
    losing_bet = show_decision_session(result["id"], db_path=db_path)["bets"][1]

    resolved = resolve_bet_selection(
        losing_bet["id"],
        outcome_status="lost",
        db_path=db_path,
        provider_status="settled",
        provider_result="yes",
        provider_settlement_value_cents=100,
        provider_close_time="2026-03-27T08:00:00Z",
        observed_high_temperature_f=93.2,
        notes="Synced from Kalshi",
    )

    assert resolved["bet"]["outcome_status"] == "lost"
    assert resolved["bet"]["provider_result"] == "yes"
    assert resolved["bet"]["provider_settlement_value_cents"] == 100
    assert resolved["bet"]["simulated_gross_payout_cents"] == 0
    assert resolved["bet"]["simulated_net_pnl_cents"] == -800
