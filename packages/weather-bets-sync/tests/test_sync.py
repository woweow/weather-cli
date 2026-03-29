from __future__ import annotations

import json
from pathlib import Path

from weather_bets.application import record_decision_session, show_decision_session
from weather_bets_sync.application import sync_open_kalshi_bets


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "weather-dashboard-cli"
    / "tests"
    / "fixtures"
    / "sample_dashboard.json"
)


class StubKalshiClient:
    def get_markets(self, series_ticker=None, *, status="open", event_ticker=None, tickers=None, limit=1000):
        assert status in {"settled", "determined"}
        if event_ticker == "KXHIGHTSEA-26MAR26":
            return [
                {
                    "ticker": "KXHIGHTSEA-26MAR26-B53.5",
                    "status": "settled",
                    "result": "yes",
                    "settlement_value_dollars": "1.0000",
                    "close_time": "2026-03-27T08:00:00Z",
                }
            ]
        if event_ticker == "KXHIGHTLV-26MAR26":
            return [
                {
                    "ticker": "KXHIGHTLV-26MAR26-B92.5",
                    "status": "settled",
                    "result": "yes",
                    "settlement_value_dollars": "1.0000",
                    "close_time": "2026-03-27T08:00:00Z",
                }
            ]
        return []


class StubWeatherService:
    def fetch_observed_high_for_date(self, place: str, event_date: str):
        mapping = {
            ("Seattle,WA", "2026-03-26"): 52.0,
            ("Las Vegas,NV", "2026-03-26"): 93.2,
        }
        return {
            "location": {"input": place},
            "event_date": event_date,
            "observed_high_temperature_f": mapping[(place, event_date)],
        }


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_sync_open_kalshi_bets_settles_rows(tmp_path):
    db_path = tmp_path / "bets.db"
    record_decision_session(load_fixture(), db_path=db_path, saved_at="2026-03-27T18:00:00+00:00")

    result = sync_open_kalshi_bets(
        db_path=db_path,
        client=StubKalshiClient(),
        weather_service=StubWeatherService(),
    )

    assert result["settled_count"] == 2
    assert {row["outcome_status"] for row in result["settled"]} == {"won", "lost"}
    by_ticker = {row["provider_market_ticker"]: row for row in result["settled"]}
    assert by_ticker["KXHIGHTSEA-26MAR26-B53.5"]["observed_high_temperature_f"] == 52.0
    assert by_ticker["KXHIGHTLV-26MAR26-B92.5"]["simulated_net_pnl_cents"] == -800


def test_sync_open_kalshi_bets_supports_dry_run(tmp_path):
    db_path = tmp_path / "bets.db"
    result = record_decision_session(load_fixture(), db_path=db_path, saved_at="2026-03-27T18:05:00+00:00")
    bet_ids = [bet["id"] for bet in show_decision_session(result["id"], db_path=db_path)["bets"]]

    preview = sync_open_kalshi_bets(
        db_path=db_path,
        dry_run=True,
        bet_ids=[bet_ids[0]],
        client=StubKalshiClient(),
        weather_service=StubWeatherService(),
    )

    assert preview["settled_count"] == 0
    assert len(preview["dry_run_rows"]) == 1
    assert preview["dry_run_rows"][0]["outcome_status"] == "won"
