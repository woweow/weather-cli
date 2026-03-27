Purpose: the local source of truth for recorded decision sessions and manual settlement.

Owns:

- the normalized dashboard snapshot contract
- the SQLite schema and migrations
- session recording and selected-bet normalization
- manual settlement and machine-readable inspection commands

Does not own:

- live weather fetching
- live market fetching
- dashboard UI rendering

Validation:

1. Run `uv run pytest packages/weather-bets/tests -q`.
2. For end-to-end validation, serve a dashboard, record a session through the UI, then verify it via `weather-bets sessions`, `weather-bets bets`, and `weather-bets settle`.
