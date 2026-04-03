Kalshi API keys should not be read directly, but can be fetched from the env: KALSHI_API_KEY_READONLY, KALSHI_API_JEY_ID

Example: for the remaining hours of today in Seattle, run `uv run --package weather-cli weather "Seattle,WA" --range next-24h --format json` and keep only forecast periods later than now that still fall on the current local date.

This is a local-only personal project. Not looking to scale to the cloud or come off of this machine.

Clean-slate policy:

- Prefer replacement over backwards-compatibility code.
- Old SQLite data, old snapshot shapes, and old CLI aliases may be deleted rather than migrated.
- If the journal schema is incompatible, fail fast and recreate it with `weather-bets init --reset`.

Layer hierarchy:

- `packages/weather-cli`: NOAA and geocoding source adapter. It fetches and normalizes weather data only.
- `packages/kalshi-weather-markets-cli`: Kalshi source adapter. It fetches and normalizes market ladders only.
- `packages/weather-bets`: local journal and decision contract. It owns the SQLite DB, migrations, session recording, settlement, and machine-readable reads.
- `packages/weather-bets-sync`: reconciliation/orchestration layer. It reads unresolved provider-backed bets, fetches settlement data, enriches with NOAA observed highs, and writes outcomes back through `weather-bets`.
- `packages/weather-dashboard-cli`: local presentation app. It serves the UI and browser APIs, but writes through `weather-bets`.
- `skills/build-weather-bet-dashboard`: orchestration only. It should call the installed CLIs, not reach into package internals when a CLI exists.

Dependency rules:

- Source adapter packages do not depend on `weather-bets` or `weather-dashboard-cli`.
- `weather-bets` does not fetch live weather or Kalshi data and does not render UI.
- `weather-bets-sync` may depend on source adapters and `weather-bets`, but does not own raw SQL, dashboard rendering, or provider ladder presentation.
- `weather-dashboard-cli` may depend on `weather-bets`, but not on source adapters.
- Skills may orchestrate CLIs across layers, but should not become a hidden runtime layer.

Settlement rules:

- Provider settlement is authoritative for `won`, `lost`, or `void`.
- NOAA observed highs are supplemental analysis data only and must not override provider settlement.
- Exact provider ids matter: prefer `provider_event_ticker` and `provider_market_ticker` over human labels.

Default validation after changes:

1. Run `uv run pytest -q`.
2. If the change touches the journal schema, recreate it with `weather-bets init --reset`.
3. For anything touching the journal or dashboard, start `weather-dashboard serve --input <dashboard.json>`.
4. Use Playwright MCP to open the UI, toggle selections, enter stakes, click Record, and verify the session via `weather-bets sessions` and `weather-bets bets`.
5. Run `weather-bets settle --bet-id <id> ...` and verify the updated row through the CLI.
6. For provider settlement work, run `weather-bets-sync kalshi settle-open [--dry-run]` and verify the updated rows through `weather-bets bets`.

## Cursor Cloud specific instructions

### Environment

- Python 3.12 and `uv` are pre-installed. `uv` lives at `~/.local/bin/uv`; make sure `$PATH` includes `$HOME/.local/bin`.
- `uv sync` at the workspace root installs all 7 packages in editable mode into `.venv/`.
- `pytest` is not a declared dev dependency. Run tests with `uv run --with pytest pytest -q`.

### Running the dashboard end-to-end

The `skills/build-weather-bet-dashboard/scripts/build_dashboard.py` currently emits `schema_version: "1"`, but the dashboard server requires version `"2"`. To build a working dashboard JSON, assemble it manually from the CLI outputs:

1. Fetch weather: `uv run --package weather-cli weather "Seattle,WA" --range next-24h --format json`
2. Fetch market: `uv run --package kalshi-weather-markets-cli kalshi-weather-markets Seattle --format json`
3. Build `dashboard.json` with `schema_version: "2"`. Map the market `ticker` field to `provider_market_ticker` in the dashboard rows.
4. Serve: `uv run --package weather-dashboard-cli weather-dashboard serve --input dashboard.json --host 0.0.0.0 --port 8765`
5. Initialize the journal first if needed: `uv run --package weather-bets weather-bets init --reset`

### Key CLI commands (see README.md for full list)

- Weather: `uv run --package weather-cli weather "<City,ST>" --range today --format json`
- Markets: `uv run --package kalshi-weather-markets-cli kalshi-weather-markets --list-cities`
- Journal: `uv run --package weather-bets weather-bets sessions` / `weather-bets bets`
- Sync: `uv run --package weather-bets-sync weather-bets-sync kalshi settle-open --dry-run`

### Gotchas

- All packages use only the Python standard library (no pip dependencies beyond workspace internals).
- The NOAA and Kalshi APIs require outbound HTTPS; tests mock HTTP calls and work offline.
- The SQLite journal lives at `.bets/bets.db` relative to the workspace root.
