Purpose: local presentation app for the weather/Kalshi decision UI.

Owns:

- browser-facing HTTP routes
- dashboard HTML/JS rendering, including yes/no toggles and per-side USD stake inputs
- the `weather-dashboard` CLI entrypoint

Does not own:

- SQLite schema or write rules
- live NOAA fetching
- live Kalshi fetching
- provider reconciliation

Rules:

- Persist through `weather-bets`; do not write ad hoc files here.
- `serve` is the primary user flow. `export-html` is secondary.
- The UI may preview simulator math, but persistence and settlement rules stay in `weather-bets`.

Validation:

1. Run `uv run pytest packages/weather-dashboard-cli/tests -q`.
2. Validate the UI write path with Playwright plus `weather-bets` read commands.
3. If the write path changed, run `weather-bets-sync kalshi settle-open --dry-run` against the recorded DB to verify the provider ids can be reconciled.
