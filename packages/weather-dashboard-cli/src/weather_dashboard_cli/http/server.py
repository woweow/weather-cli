from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from weather_bets.application.journal import record_decision_session
from weather_bets.paths import DEFAULT_DB_PATH
from weather_dashboard_cli.ui import render_dashboard_html


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def create_server(
    *,
    payload: dict[str, Any],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> ThreadingHTTPServer:
    handler = build_handler(payload, Path(db_path).expanduser().resolve())
    return ThreadingHTTPServer((host, port), handler)


def serve_forever(
    *,
    payload: dict[str, Any],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    server = create_server(payload=payload, host=host, port=port, db_path=db_path)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def build_handler(initial_payload: dict[str, Any], db_path: Path) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:  # noqa: N802
            if self.path != "/api/decision-sessions":
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/" or self.path == "/index.html":
                self._write_html(200, render_dashboard_html(initial_payload, save_endpoint="/api/decision-sessions"))
                return
            if self.path == "/health":
                self._write_json(200, {"status": "ok"})
                return
            self._write_json(404, {"error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/decision-sessions":
                self._write_json(404, {"error": "Not found"})
                return
            try:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                payload = json.loads(body.decode("utf-8"))
                result = record_decision_session(payload, db_path=db_path)
            except json.JSONDecodeError:
                self._write_json(400, {"error": "Request body must be valid JSON."})
                return
            except Exception as exc:
                self._write_json(400, {"error": str(exc)})
                return
            self._write_json(
                200,
                {
                    "saved_at": result["saved_at"],
                    "session_id": result["id"],
                    "selection_count": result["selection_count"],
                    "db_path": result["db_path"],
                },
            )

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def _write_json(self, status: int, payload: dict[str, Any]) -> None:
            encoded = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _write_html(self, status: int, document: str) -> None:
            encoded = document.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    return DashboardHandler
