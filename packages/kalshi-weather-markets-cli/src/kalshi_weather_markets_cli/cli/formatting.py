from __future__ import annotations

import json

from kalshi_weather_markets_cli.application.models import LadderSnapshot


def render_json(snapshot: LadderSnapshot) -> str:
    return json.dumps(snapshot.to_dict(), indent=2, sort_keys=True)


def render_text(snapshot: LadderSnapshot) -> str:
    headers = ("Range", "Yes bid", "Yes ask", "No bid", "No ask", "Last")
    rows = [
        (
            market.label,
            format_cents(market.yes_bid_cents),
            format_cents(market.yes_ask_cents),
            format_cents(market.no_bid_cents),
            format_cents(market.no_ask_cents),
            format_cents(market.last_price_cents),
        )
        for market in snapshot.markets
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    header_line = "  ".join(
        header.ljust(widths[index]) for index, header in enumerate(headers)
    )
    divider = "  ".join("-" * width for width in widths)
    row_lines = [
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]
    lines = [
        snapshot.series_title,
        f"City: {snapshot.city}",
        f"Series: {snapshot.series_ticker}",
        f"Event: {snapshot.event_date_label} ({snapshot.event_ticker})",
        "",
        header_line,
        divider,
        *row_lines,
    ]
    return "\n".join(lines)


def format_cents(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{value}\u00a2"
