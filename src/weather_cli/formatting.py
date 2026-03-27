from __future__ import annotations

import json
from typing import Any


def render_output(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=False)
    if output_format == "table":
        return render_table(payload)
    raise ValueError(f"Unsupported output format {output_format!r}")


def render_table(payload: dict[str, Any]) -> str:
    lines = []
    location = payload["location"]
    range_info = payload["range"]
    lines.append(f"Location: {location['city']}, {location['state']}")
    lines.append(
        f"Coordinates: {payload['resolved_coordinates']['latitude']:.5f}, "
        f"{payload['resolved_coordinates']['longitude']:.5f}"
    )
    lines.append(
        f"Range: {range_info['name']} ({range_info['start']} -> {range_info['end']})"
    )

    station = payload.get("station")
    if station:
        station_label = station["identifier"]
        if station.get("name"):
            station_label = f"{station_label} - {station['name']}"
        lines.append(f"Station: {station_label}")
    else:
        lines.append("Station: forecast gridpoint")

    lines.append("")
    rows = _render_rows(payload["periods"])
    if not rows:
        lines.append("(no periods)")
        return "\n".join(lines)

    headers = list(rows[0].keys())
    widths = {header: max(len(header), *(len(row[header]) for row in rows)) for header in headers}
    header_line = "  ".join(header.ljust(widths[header]) for header in headers)
    separator_line = "  ".join("-" * widths[header] for header in headers)
    lines.append(header_line)
    lines.append(separator_line)

    for row in rows:
        lines.append("  ".join(row[header].ljust(widths[header]) for header in headers))

    return "\n".join(lines)


def _render_rows(periods: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for period in periods:
        if period["kind"] == "observation":
            rows.append(
                {
                    "timestamp": period["start"],
                    "temp_f": _format_number(period.get("temperature_f")),
                    "humidity_pct": _format_percent(period.get("relative_humidity_pct")),
                    "wind_mph": _format_number(period.get("wind_speed_mph")),
                    "summary": period.get("summary") or "",
                }
            )
        else:
            rows.append(
                {
                    "start": period["start"],
                    "end": period["end"],
                    "temp_f": _format_number(period.get("temperature_f")),
                    "precip_pct": _format_percent(period.get("precipitation_probability_pct")),
                    "wind": _stringify(period.get("wind_speed")),
                    "summary": period.get("summary") or "",
                }
            )
    return rows


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return f"{int(value)}"
    return f"{value:.1f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return f"{int(value)}%"
    return f"{value:.1f}%"


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
