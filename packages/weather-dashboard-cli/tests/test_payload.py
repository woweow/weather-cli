from __future__ import annotations

import json
from pathlib import Path

import pytest

from weather_dashboard_cli.errors import PayloadValidationError
from weather_dashboard_cli.payload import dashboard_file_name, normalize_dashboard_payload


FIXTURE = Path(__file__).parent / "fixtures" / "sample_dashboard.json"


def test_normalize_dashboard_payload_sets_default_selection_state():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del payload["cards"][0]["market"]["rows"][0]["selected_yes"]
    del payload["cards"][0]["market"]["rows"][0]["selected_no"]

    normalized = normalize_dashboard_payload(payload)

    row = normalized["cards"][0]["market"]["rows"][0]
    assert row["selected_yes"] is False
    assert row["selected_no"] is False


def test_normalize_dashboard_payload_rejects_invalid_shape():
    with pytest.raises(PayloadValidationError):
        normalize_dashboard_payload({"dashboard_date": "2026-03-27", "cards": []})


def test_dashboard_file_name_uses_day_month_year():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert dashboard_file_name(payload) == "27_03_2026_bets_placed.json"
