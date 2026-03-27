# weather-bets

Local SQLite-backed journal for recorded weather bet decisions.

The package owns:

- the normalized dashboard snapshot contract
- SQLite schema and migrations
- decision-session recording
- selected-bet normalization
- manual settlement
- machine-readable inspection commands

Examples:

```bash
uv run --package weather-bets weather-bets init
uv run --package weather-bets weather-bets sessions --limit 5
uv run --package weather-bets weather-bets bets --status open
uv run --package weather-bets weather-bets settle --bet-id 12 --status won --payout-cents 100
```
