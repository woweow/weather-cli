# weather-study-cli

Local CLI for the forecast-confidence and market-opportunity study described in the root `PRD.md`.

Current scope:

- checked-in mock raw city-hour captures
- raw capture schema validation
- one local loader path that works for the bundled mock tree and future S3 downloads copied to disk
- dedicated SQLite study schema plus first raw ingest path into normalized tables
- NOAA-backed daily actual-high derivation for completed local dates
- hourly forecast-confidence metric derivation into `hourly_accuracy_metrics`
- exported local HTML visualization for the hourly accuracy view

Examples:

```bash
uv run --package weather-study-cli weather-study validate-raw
uv run --package weather-study-cli weather-study validate-raw --input packages/weather-study-cli/mock-data/raw --format json
uv run --package weather-study-cli weather-study ingest-raw --reset
uv run --package weather-study-cli weather-study derive-daily-actuals --db-path /tmp/weather-study.db
uv run --package weather-study-cli weather-study compute-accuracy-metrics --db-path /tmp/weather-study.db
uv run --package weather-study-cli weather-study export-accuracy-html --db-path /tmp/weather-study.db --output /tmp/weather-study.html
```

Notes:

- The raw capture contract keeps weather and market payloads separate and immutable.
- Files are stored with S3-style path metadata such as `study_version=1/city=Seattle/...`.
- Partial failures are valid as long as one source payload remains present and the missing source is recorded in `errors`.
- `ingest-raw` creates a local SQLite database at `.study/weather-study.db` by default and populates `raw_captures`, `forecast_periods`, and `market_rows`, with placeholder tables for later daily actuals and derived metrics.
- `derive-daily-actuals` reads distinct place/date pairs from `raw_captures`, skips any local date that has not finished yet in that city's timezone, and upserts NOAA observed highs into `daily_actuals`.
- `compute-accuracy-metrics` derives the first hourly forecast-confidence rows from `raw_captures` plus `daily_actuals`, including valid, missing, excluded, and correct day counts.
- `export-accuracy-html` writes a self-contained local page with a city selector, an hourly accuracy chart, coverage cards, and thin-sample warnings backed by `hourly_accuracy_metrics`.
- This package is the home for future SQLite ingest, derivations, and study visualization. It does not write to `.bets/bets.db`.
