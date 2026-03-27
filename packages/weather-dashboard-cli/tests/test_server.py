from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from weather_bets.application import list_bet_selections, list_decision_sessions, show_decision_session
from weather_bets.domain.snapshot import normalize_dashboard_snapshot
from weather_dashboard_cli.http import create_server


FIXTURE = Path(__file__).parent / "fixtures" / "sample_dashboard.json"


def test_server_records_sessions_to_sqlite(tmp_path):
    payload = normalize_dashboard_snapshot(json.loads(FIXTURE.read_text(encoding="utf-8")))
    db_path = tmp_path / "bets.db"
    server = create_server(payload=payload, host="127.0.0.1", port=0, db_path=db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/decision-sessions"
        for _ in range(2):
            request = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request) as response:
                assert response.status == 200
                body = json.load(response)
                assert body["selection_count"] == 2

        sessions = list_decision_sessions(db_path=db_path)
        bets = list_bet_selections(db_path=db_path)

        assert len(sessions["sessions"]) == 2
        assert len(bets["bets"]) == 4

        first_session_id = sessions["sessions"][0]["id"]
        session = show_decision_session(first_session_id, db_path=db_path)
        assert session["snapshot"]["cards"][0]["market"]["rows"][1]["selected_yes"] is True
    finally:
        server.shutdown()
        thread.join(timeout=5)
