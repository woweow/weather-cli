# kalshi-weather-markets-cli

Small Python CLI for inspecting Kalshi daily high-temperature markets for a city.

Examples:

```bash
uv run --package kalshi-weather-markets-cli kalshi-weather-markets Seattle
uv run --package kalshi-weather-markets-cli kalshi-weather-markets --list-cities
uv run --package kalshi-weather-markets-cli kalshi-weather-markets Seattle --format json
```

Notes:

- The CLI reads Kalshi's public market-data endpoints directly. It does not require API keys.
- City input is exact-name based in v1. Use `--list-cities` to see the supported city names.
- Output defaults to readable text; `--format json` returns the normalized snapshot payload.
- JSON output contains the full active ladder for the selected daily event, sorted by
  temperature range.
- Each ladder row includes the raw `last_price_cents` headline value plus Yes/No bid and ask
  fields. This shape is intended to feed `weather-dashboard generate-html`.
