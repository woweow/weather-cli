# weather-dashboard-cli

Small Python CLI for serving the local weather/Kalshi decision UI from a normalized
JSON payload, plus a secondary HTML export path.

Commands:

```bash
uv run --package weather-dashboard-cli weather-dashboard serve --input dashboard.json
uv run --package weather-dashboard-cli weather-dashboard export-html --input dashboard.json --output dashboard.html
uv run --package weather-bets weather-bets sessions
```

Notes:

- `serve` is the primary flow. It renders the UI at `GET /` and records sessions at
  `POST /api/decision-sessions`.
- `export-html` accepts JSON from stdin or `--input`.
- The payload is normalized card data prepared by an external agent or script.
- Each market row must include provider ids and may include per-side `yes_stake_usd` / `no_stake_usd`.
- `weather_hours` should contain hourly forecast rows from each city's local current time
  through local midnight.
- `market.rows` should contain the full active Kalshi ladder for the selected daily event.
- `last_price_cents` is the primary per-row headline value shown in the dashboard.
- The browser saves the full snapshot, selected side, stake, displayed quote, and provider market id.
- Recorded sessions are written into the SQLite journal at
  `/Users/brianrogers/coding/weather-cli/.bets/bets.db` by default.
- Manual settlement and DB inspection happen through `weather-bets`.
- Automatic Kalshi reconciliation happens through `weather-bets-sync`.
