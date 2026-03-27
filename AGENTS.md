Kalshi API keys should not be read directly, but can be fetched from the env: KALSHI_API_KEY_READONLY, KALSHI_API_JEY_ID

Example: for the remaining hours of today in Seattle, run `uv run --package weather-cli weather "Seattle,WA" --range next-24h --format json` and keep only forecast periods later than now that still fall on the current local date.
