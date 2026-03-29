# weather-bets-sync

Automatic reconciliation for unresolved journal rows.

## Commands

```bash
uv run --package weather-bets-sync weather-bets-sync kalshi settle-open --dry-run
uv run --package weather-bets-sync weather-bets-sync kalshi settle-open --db-path .bets/bets.db
```

This package reads unresolved selections from `weather-bets`, fetches Kalshi settlement data,
optionally enriches the result with NOAA observed highs, and writes the outcome back through
`weather-bets`.

Notes:

- Kalshi settlement is authoritative for `won`, `lost`, or `void`.
- NOAA observed highs are supplemental only.
- Matching is done by exact `provider_market_ticker`, not by market label.
