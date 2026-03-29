# weather-cli workspace

This repo now contains multiple Python CLIs in a small `uv` workspace:

- `weather-cli`: NOAA observations and forecast windows
- `kalshi-weather-markets-cli`: Kalshi daily high-temperature market snapshots
- `weather-dashboard-cli`: local dashboard server and HTML export
- `weather-study-cli`: raw study schema validation, mock data, and future ingest/analytics home
- `weather-study-collector`: live raw study capture assembly for local disk and future S3 upload
- `weather-bets`: local SQLite journal for recorded decisions and settlement
- `weather-bets-sync`: automatic provider reconciliation for unresolved journal rows

## Commands

```bash
uv run --package weather-cli weather "Seattle,WA" --range today
uv run --package kalshi-weather-markets-cli kalshi-weather-markets Seattle
uv run --package kalshi-weather-markets-cli kalshi-weather-markets --list-cities
uv run --package weather-study-cli weather-study validate-raw
uv run --package weather-study-cli weather-study sync-s3 --help
uv run --package weather-study-cli weather-study ingest-raw --help
uv run --package weather-study-cli weather-study derive-daily-actuals --help
uv run --package weather-study-cli weather-study compute-accuracy-metrics --help
uv run --package weather-study-cli weather-study export-accuracy-html --help
uv run --package weather-study-collector -- weather-study-collector capture --help
uv run --package weather-dashboard-cli weather-dashboard serve --help
uv run --package weather-dashboard-cli weather-dashboard export-html --help
uv run --package weather-bets weather-bets sessions --help
uv run --package weather-bets-sync weather-bets-sync kalshi settle-open --help
```

## Architecture

- `weather-cli` fetches NOAA observations and forecast windows.
- `kalshi-weather-markets-cli` fetches Kalshi weather ladders and exposes stable provider ids.
- `weather-study-cli` owns the raw study capture contract, checked-in mock captures, and the local loader/validator path that later ingest/analytics/visualization will build on.
- `weather-study-collector` owns live city-hour capture orchestration and writes schema-valid raw study files to disk with one-side failure persistence.
- `weather-dashboard-cli` renders the local decision UI, collects yes/no selections plus simulated USD stakes, and posts the full snapshot to the journal.
- `weather-bets` owns the canonical snapshot contract, the SQLite database at `.bets/bets.db`, manual settlement, and machine-readable reads.
- `weather-bets-sync` reads unresolved provider-backed rows from `weather-bets`, fetches settlement data, enriches with NOAA observed highs, and writes the settled outcome back through `weather-bets`.

This workspace is intentionally local-first and clean-slate. Old DBs or legacy snapshot shapes should be replaced rather than migrated.

## Layout

```text
packages/
  weather-cli/
  kalshi-weather-markets-cli/
  weather-study-cli/
  weather-study-collector/
  weather-dashboard-cli/
  weather-bets/
  weather-bets-sync/
skills/
```

Each package owns its own `pyproject.toml`, source tree, tests, and `AGENTS.md`. The root
`uv.lock` covers the workspace.
