from __future__ import annotations

import json
from pathlib import Path

from weather_bets.application import (
    list_bet_selections,
    list_decision_sessions,
    record_decision_session,
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


def test_record_decision_session_persists_snapshot_and_normalized_rows(tmp_path):
    db_path = tmp_path / "bets.db"

    result = record_decision_session(load_fixture(), db_path=db_path, saved_at="2026-03-27T18:00:00+00:00")
    session = show_decision_session(result["id"], db_path=db_path)

    assert result["selection_count"] == 2
    assert session["snapshot"]["cards"][0]["market"]["rows"][1]["selected_yes"] is True
    assert [bet["side"] for bet in session["bets"]] == ["yes", "no"]


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


def test_settle_bet_selection_updates_one_open_bet(tmp_path):
    db_path = tmp_path / "bets.db"
    result = record_decision_session(load_fixture(), db_path=db_path, saved_at="2026-03-27T18:10:00+00:00")
    bet_id = show_decision_session(result["id"], db_path=db_path)["bets"][0]["id"]

    settled = settle_bet_selection(
        bet_id,
        status="won",
        db_path=db_path,
        resolved_at="2026-03-28T09:00:00+00:00",
        actual_temperature_f=54,
        payout_cents=100,
        notes="Manual settlement",
    )

    bets = list_bet_selections(db_path=db_path, status="settled")
    assert settled["bet"]["outcome_status"] == "won"
    assert bets["bets"][0]["payout_cents"] == 100

