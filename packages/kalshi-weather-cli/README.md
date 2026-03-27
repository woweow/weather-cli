# kalshi-weather-cli

Small Python CLI for inspecting Kalshi daily high-temperature markets for a city.

Examples:

```bash
uv run --package kalshi-weather-cli kalshi-weather Seattle
uv run --package kalshi-weather-cli kalshi-weather --list-cities
uv run --package kalshi-weather-cli kalshi-weather Seattle --format json
```

Notes:

- The CLI reads Kalshi's public market-data endpoints directly. It does not require API keys.
- City input is exact-name based in v1. Use `--list-cities` to see the supported city names.
- Output defaults to readable text; `--format json` returns the normalized snapshot payload.
