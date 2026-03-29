Purpose: the local source of truth for recorded decision sessions and manual settlement.

Owns:

- the canonical dashboard snapshot contract, including provider ids and per-side stake fields
- simulator math inputs and settlement outputs
- the SQLite schema, clean-slate initialization, and repository-level persistence
- session recording, selected-bet normalization, manual settlement, and machine-readable inspection commands

Does not own:

- live weather fetching
- live market fetching
- dashboard UI rendering
- reconciliation against external providers

Validation:

1. Run `uv run pytest packages/weather-bets/tests -q`.
2. If the schema changed, recreate the DB with `uv run --package weather-bets weather-bets init --reset`.
3. For end-to-end validation, serve a dashboard, record a session through the UI, then verify it via `weather-bets sessions`, `weather-bets bets`, and `weather-bets settle`.
