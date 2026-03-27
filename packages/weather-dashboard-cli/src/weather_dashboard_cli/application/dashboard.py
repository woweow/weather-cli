from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from weather_bets.domain.snapshot import load_dashboard_snapshot as load_snapshot
from weather_dashboard_cli.ui import render_dashboard_html


def load_dashboard_snapshot_for_app(input_path: str | None) -> dict[str, Any]:
    return load_snapshot(input_path)


def export_dashboard_html(
    input_path: str | None,
    output_path: str | None,
    *,
    save_endpoint: str,
) -> int:
    payload = load_dashboard_snapshot_for_app(input_path)
    html = render_dashboard_html(payload, save_endpoint=save_endpoint)
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
    else:
        sys.stdout.write(html)
    return 0


load_dashboard_snapshot = load_dashboard_snapshot_for_app
