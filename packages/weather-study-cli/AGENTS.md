Purpose: the local weather-market study package.

Owns the raw study capture contract, mock data, loader/validator, SQLite ingest, daily actuals derivation, forecast accuracy metrics, market opportunity metrics, gap reporting, and the self-contained HTML visualization export.

Rules:

- Do not depend on `weather-bets` or `weather-dashboard-cli`.
- Use existing adapter CLIs/packages as upstream inputs rather than reimplementing NOAA or Kalshi fetching here.
- The study DB is resettable by design. Schema bumps should fail fast; rebuild from raw captures with `ingest-raw --reset`.
- Partial failures are valid raw captures as long as one source payload is present and the missing source is recorded in `errors`.

Key commands:

- `uv run --package weather-study-cli weather-study validate-raw` — validate bundled mock raw captures
- `uv run --package weather-study-cli weather-study ingest-raw --reset --db-path <path>` — rebuild study DB from raw files
- `uv run --package weather-study-cli weather-study build-report --db-path <path> --output <path>.html --format text` — one-shot pipeline from raw captures to HTML export

See `docs/live-data-and-report-workflow.md` for the full live-data and mock-data report workflows.

Default validation after changes:

1. Run `uv run pytest -q`.
2. Run `uv run --package weather-study-cli weather-study build-report --db-path /tmp/weather-study-test.db --output /tmp/weather-study-test.html --format text` and confirm it completes.
