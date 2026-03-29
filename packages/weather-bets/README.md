# weather-bets

Local SQLite-backed journal for recorded weather bet decisions.

The package owns:

- the normalized dashboard snapshot contract, including provider ids and per-side simulator stakes
- SQLite schema, clean-slate initialization, and journal storage at `.bets/bets.db`
- decision-session recording
- selected-bet normalization
- manual settlement plus simulator payout/P&L calculation
- machine-readable inspection commands

Examples:

```bash
uv run --package weather-bets weather-bets init
uv run --package weather-bets weather-bets init --reset
uv run --package weather-bets weather-bets sessions --limit 5
uv run --package weather-bets weather-bets bets --status open
uv run --package weather-bets weather-bets settle --bet-id 12 --status won --payout-cents 100
```

Notes:

- This package does not fetch live Kalshi or NOAA data.
- Provider-backed auto settlement belongs in `weather-bets-sync`.
- Incompatible older DBs are intentionally not migrated; recreate them with `weather-bets init --reset`.
