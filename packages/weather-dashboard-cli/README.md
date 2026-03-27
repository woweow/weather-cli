# weather-dashboard-cli

Small Python CLI for rendering a static HTML weather and Kalshi dashboard from a
normalized JSON payload, plus a local save endpoint for recording bet selections.

Commands:

```bash
uv run --package weather-dashboard-cli weather-dashboard generate-html --input dashboard.json --output dashboard.html
uv run --package weather-dashboard-cli weather-dashboard serve-bets
```

Notes:

- `generate-html` accepts JSON from stdin or `--input`.
- The payload is normalized card data prepared by an external agent or script.
- `weather_hours` should contain hourly forecast rows from each city's local current time
  through local midnight.
- `market.rows` should contain the full active Kalshi ladder for the selected daily event.
- `last_price_cents` is the primary per-row headline value shown in the dashboard.
- `serve-bets` writes dated snapshot files into the fixed repo path
  `/Users/brianrogers/coding/weather-cli/.bets`.
- Saved records append to `DD_MM_YYYY_bets_placed.json`.
- The generated HTML can render without the save server, but the `Record bets` button only
  persists data while `weather-dashboard serve-bets` is running.
