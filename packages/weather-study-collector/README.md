# weather-study-collector

Local collector for live weather-market study raw captures.

Current scope:

- centralized supported-city list for the study collector
- live hourly raw capture assembly using `weather-cli` and `kalshi-weather-markets-cli`
- schema validation against `weather-study-cli` before any file is written
- local filesystem output using the same path shape as future S3 downloads
- partial-failure persistence when weather or market capture fails independently

Examples:

```bash
uv run --package weather-study-collector -- weather-study-collector capture
uv run --package weather-study-collector -- weather-study-collector capture --place Seattle,WA --output-root /tmp/weather-study-live
uv run --package weather-study-collector -- weather-study-collector capture --captured-at-utc 2026-03-29T21:00:00Z --format json
uv run --package weather-study-collector -- weather-study-collector capture-s3 --bucket <bucket> --prefix raw-live
```

Notes:

- The collector writes files rooted at `study_version=.../city=.../state=...` so `weather-study validate-raw` and `ingest-raw` can read them unchanged.
- `capture-s3` reuses that same raw tree shape in a temp directory and syncs it to `s3://<bucket>/<prefix>/` with the AWS CLI (default: no `--profile`; use `--profile dev` if you use named profiles).
- Captures default to the current UTC hour. Explicit `--captured-at-utc` values must also be UTC top-of-hour timestamps.
- Weather and market fetches are independent. If one side fails, the other side is still persisted with an `errors` entry.
- If both weather and market fail for a city, no raw file is written for that city-hour.
