Purpose: reconcile unresolved provider-backed journal rows and write settled outcomes back through `weather-bets`.

Owns:

- reconciliation/orchestration flows across the journal and provider adapters
- automatic settlement logic for supported providers
- exact-match provider reconciliation using stored provider ids
- the `weather-bets-sync` CLI entrypoint

Does not own:

- SQLite schema or raw SQL
- dashboard rendering
- provider-specific weather ladder presentation

Validation:

1. Run `uv run pytest packages/weather-bets-sync/tests -q`.
2. Validate one end-to-end path by recording a session, running `weather-bets-sync kalshi settle-open`, and verifying the updated rows through `weather-bets bets`.
3. Treat provider settlement as authoritative and NOAA observed highs as supplemental only.
