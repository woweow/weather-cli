# Weather Study Runbook

How to generate the weekly sample dataset, pull live data, build the study database, and view the visualization.

## Quick reference

| What | Command |
|------|---------|
| Refresh bundled weekly sample data | `uv run --package weather-study-cli weather-study generate-sample-data --format text` |
| Mock report (no AWS needed) | `uv run --package weather-study-cli weather-study build-report --db-path /tmp/weather-study.db --output /tmp/weather-study.html --format text` |
| Live report (pulls from S3) | See "Live data" section below |
| Archive or fetch old live datasets | See `docs/old-dataset-runbook.md` |
| Open the report | `open /tmp/weather-study.html` (or serve with `python3 -m http.server -d /tmp`) |

## Mock data report

Uses the checked-in sample raw dataset under `packages/weather-study-cli/mock-data/raw/`. No AWS credentials or S3 access required. The default sample covers Seattle and Denver across the last 7 completed local dates with hourly captures for the full day.

If you want to refresh that bundled sample dataset and metadata manifest before building the report:

```bash
uv run --package weather-study-cli weather-study generate-sample-data \
  --format text
```

This command rebuilds:

- `packages/weather-study-cli/mock-data/raw/`
- `packages/weather-study-cli/mock-data/sample-week-metadata.json`

It fetches NOAA observed highs for the sampled dates, then writes synthetic hourly forecast and market snapshots that intentionally converge toward the observed daily winner through the day.

```bash
uv run --package weather-study-cli weather-study build-report \
  --db-path /tmp/weather-study-mock.db \
  --output /tmp/weather-study-mock.html \
  --format text
```

This runs the full pipeline in one shot: ingest raw captures → derive daily actuals from NOAA → compute forecast accuracy metrics → compute market opportunity metrics → export HTML.

The HTML export is now intentionally narrow:

- One chart per city
- X-axis: local hour
- Y-axis: percent of resolved days where that hour's forecast got the final high right
- Under each hour: representative winning market label plus the average winner price at that hour

## Live data report

Pulls real captures from S3, rebuilds the study DB, and exports the visualization.

**Prerequisites:** AWS CLI configured with a `dev` profile that has read access to the study bucket.

**Bucket:** `weather-study-raw-084375548651-us-west-2`
**Live prefix:** `raw/`
**Region:** `us-west-2`

If you need to cut old captures out of the active live prefix while preserving them for later analysis, follow `packages/weather-study-cli/docs/old-dataset-runbook.md`.

```bash
uv run --package weather-study-cli weather-study build-report \
  --bucket weather-study-raw-084375548651-us-west-2 \
  --prefix raw \
  --sync-output-root /tmp/weather-study-live-raw \
  --db-path /tmp/weather-study-live.db \
  --output /tmp/weather-study-live.html \
  --format text
```

The `--sync-output-root` is where raw files are downloaded before ingest. The `--format text` flag prints a summary including city maturity (resolved days, capture windows) and gap coverage.

## What `build-report` does

1. **Sync** (optional, only with `--bucket`): `aws s3 sync` from the bucket/prefix to `--sync-output-root`
2. **Validate**: checks every downloaded raw file against the study capture schema
3. **Ingest**: resets and rebuilds the SQLite study DB from raw files (`raw_captures`, `forecast_periods`, `market_rows`)
4. **Derive daily actuals**: fetches NOAA observed highs for completed local dates
5. **Compute forecast accuracy metrics**: per-city, per-hour accuracy rates into `hourly_accuracy_metrics`
6. **Compute market opportunity metrics**: per-city, per-hour market convergence into `hourly_market_opportunity_metrics`
7. **Export HTML**: self-contained file with one per-city hourly forecast-accuracy chart and winner-price annotations beneath the hour labels

## Individual commands

If you need to run steps separately instead of using `build-report`:

```bash
# Validate raw files
uv run --package weather-study-cli weather-study validate-raw --input <raw-dir>

# Sync from S3 to local disk
uv run --package weather-study-cli weather-study sync-s3 \
  --bucket weather-study-raw-084375548651-us-west-2 \
  --prefix raw \
  --output-root /tmp/weather-study-raw

# Ingest into SQLite
uv run --package weather-study-cli weather-study ingest-raw \
  --input /tmp/weather-study-raw \
  --reset \
  --db-path /tmp/weather-study.db

# Derive daily actuals
uv run --package weather-study-cli weather-study derive-daily-actuals \
  --db-path /tmp/weather-study.db

# Compute accuracy metrics
uv run --package weather-study-cli weather-study compute-accuracy-metrics \
  --db-path /tmp/weather-study.db

# Compute market opportunity metrics
uv run --package weather-study-cli weather-study compute-market-opportunity-metrics \
  --db-path /tmp/weather-study.db

# Export HTML
uv run --package weather-study-cli weather-study export-accuracy-html \
  --db-path /tmp/weather-study.db \
  --output /tmp/weather-study.html

# Generate or refresh the bundled weekly sample dataset
uv run --package weather-study-cli weather-study generate-sample-data

# Generate sample data and upload it to S3 under a non-live prefix
uv run --package weather-study-cli weather-study generate-sample-data \
  --bucket weather-study-raw-084375548651-us-west-2 \
  --prefix sample/weather-study-weekly-2026-03-29

# Report gaps
uv run --package weather-study-cli weather-study report-gaps \
  --db-path /tmp/weather-study.db --format json

# Day drilldown
uv run --package weather-study-cli weather-study export-day-drilldown \
  --db-path /tmp/weather-study.db \
  --place "Seattle,WA" \
  --local-date 2026-03-29 \
  --format json
```

## Configured study cities

Seattle,WA · Denver,CO · San Francisco,CA · Los Angeles,CA · Las Vegas,NV · Phoenix,AZ

## Cloud collection

The Lambda `weather-study-collector-dev` runs hourly via EventBridge Scheduler (`weather-study-collector-hourly`), captures all 6 cities, and writes raw files to the live `raw/` prefix. Deploy config lives at `aws/weather-study-collector/config/dev-live.json`.

For sample/demo data uploads, prefer `weather-study generate-sample-data --bucket ... --prefix sample/...` so the synthetic weekly dataset stays isolated from the live collector's `raw/` prefix.

```bash
# Redeploy the Lambda + scheduler
python3 aws/weather-study-collector/deploy.py \
  --config aws/weather-study-collector/config/dev-live.json

# Manual one-off invoke
aws lambda invoke \
  --function-name weather-study-collector-dev \
  --profile dev --region us-west-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"places":["Seattle,WA"]}' \
  /tmp/lambda-response.json
```
