from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from weather_dashboard_cli.payload import (
    build_saved_snapshot,
    dashboard_file_name,
    normalize_dashboard_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SAVE_DIR = REPO_ROOT / ".bets"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    save_dir: Path = DEFAULT_SAVE_DIR,
) -> ThreadingHTTPServer:
    handler = build_handler(save_dir)
    return ThreadingHTTPServer((host, port), handler)


def serve_forever(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    save_dir: Path = DEFAULT_SAVE_DIR,
) -> None:
    server = create_server(host, port, save_dir=save_dir)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def build_handler(save_dir: Path) -> type[BaseHTTPRequestHandler]:
    class RecordBetsHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/record-bets":
                self._write_json(404, {"error": "Not found"})
                return
            try:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                payload = json.loads(body.decode("utf-8"))
                normalized = normalize_dashboard_payload(payload)
                saved_at = datetime.now(timezone.utc).isoformat()
                snapshot = build_saved_snapshot(normalized, saved_at)
                file_path = persist_snapshot(snapshot, save_dir=save_dir)
            except json.JSONDecodeError:
                self._write_json(400, {"error": "Request body must be valid JSON."})
                return
            except Exception as exc:
                self._write_json(400, {"error": str(exc)})
                return
            self._write_json(
                200,
                {
                    "saved_at": saved_at,
                    "file_name": file_path.name,
                    "path": str(file_path),
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

        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    return RecordBetsHandler


def persist_snapshot(snapshot: dict[str, Any], *, save_dir: Path = DEFAULT_SAVE_DIR) -> Path:
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / dashboard_file_name(snapshot)
    if file_path.exists():
        existing = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            raise ValueError(f"Existing save file {file_path} is not a JSON array.")
    else:
        existing = []
    existing.append(snapshot)
    file_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return file_path
