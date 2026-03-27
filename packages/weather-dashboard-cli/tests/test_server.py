from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from weather_dashboard_cli.payload import normalize_dashboard_payload
from weather_dashboard_cli.server import create_server


FIXTURE = Path(__file__).parent / "fixtures" / "sample_dashboard.json"


def test_server_appends_snapshots_to_dated_file(tmp_path):
    payload = normalize_dashboard_payload(json.loads(FIXTURE.read_text(encoding="utf-8")))
    server = create_server("127.0.0.1", 0, save_dir=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/record-bets"
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
                assert body["file_name"] == "27_03_2026_bets_placed.json"

        saved_file = tmp_path / "27_03_2026_bets_placed.json"
        contents = json.loads(saved_file.read_text(encoding="utf-8"))
        assert len(contents) == 2
        assert contents[0]["saved_at"]
        assert contents[1]["cards"][0]["market"]["rows"][1]["selected_yes"] is True
    finally:
        server.shutdown()
        thread.join(timeout=5)
