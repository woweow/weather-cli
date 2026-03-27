Kalshi API keys should not be read directly, but can be fetched from the env: KALSHI_API_KEY_READONLY, KALSHI_API_JEY_ID

Example: for the remaining hours of today in Seattle, run `uv run --package weather-cli weather "Seattle,WA" --range next-24h --format json` and keep only forecast periods later than now that still fall on the current local date.

This is a local-only personal project. Not looking to scale to the cloud or come off of this machine.

Layer hierarchy:

- `packages/weather-cli`: NOAA and geocoding source adapter. It fetches and normalizes weather data only.
- `packages/kalshi-weather-markets-cli`: Kalshi source adapter. It fetches and normalizes market ladders only.
- `packages/weather-bets`: local journal and decision contract. It owns the SQLite DB, migrations, session recording, settlement, and machine-readable reads.
- `packages/weather-dashboard-cli`: local presentation app. It serves the UI and browser APIs, but writes through `weather-bets`.
- `skills/build-weather-bet-dashboard`: orchestration only. It should call the installed CLIs, not reach into package internals when a CLI exists.

Dependency rules:

- Source adapter packages do not depend on `weather-bets` or `weather-dashboard-cli`.
- `weather-bets` does not fetch live weather or Kalshi data and does not render UI.
- `weather-dashboard-cli` may depend on `weather-bets`, but not on source adapters.
- Skills may orchestrate CLIs across layers, but should not become a hidden runtime layer.

Default validation after changes:

1. Run `uv run pytest -q`.
2. For anything touching the journal or dashboard, start `weather-dashboard serve --input <dashboard.json>`.
3. Use Playwright MCP to open the UI, toggle selections, click Record, and verify the session via `weather-bets sessions` and `weather-bets bets`.
4. Run `weather-bets settle --bet-id <id> ...` and verify the updated row through the CLI.
