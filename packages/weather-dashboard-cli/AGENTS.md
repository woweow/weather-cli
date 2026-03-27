Purpose: local presentation app for the weather/Kalshi decision UI.

Owns:

- browser-facing HTTP routes
- dashboard HTML/JS rendering
- the `weather-dashboard` CLI entrypoint

Does not own:

- SQLite schema or write rules
- live NOAA fetching
- live Kalshi fetching

Rules:

- Persist through `weather-bets`; do not write ad hoc files here.
- `serve` is the primary user flow. `export-html` is secondary.

Validation:

1. Run `uv run pytest packages/weather-dashboard-cli/tests -q`.
2. Validate the UI write path with Playwright plus `weather-bets` read commands.
