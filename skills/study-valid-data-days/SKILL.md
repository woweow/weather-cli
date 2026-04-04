---
name: study-valid-data-days
description: Answer questions about how many complete local days of weather-study test data exist per city (Seattle, San Francisco, Los Angeles, Las Vegas, Phoenix, Denver). Use when the user says "summarize lambda data" or asks for valid days, complete days, data coverage, or "how much study data" after S3 sync and ingest—run the fixed weather-study CLI sequence and return command output only.
---

# Study valid data days

## When this applies

Trigger phrase: **summarize lambda data**.

Also applies for: valid days of test data, complete capture days, how many days of study data, data completeness per city, incomplete days filtered out before the study UI.

## What to run (do not re-derive counts mentally)

From the repository root, with AWS credentials if syncing from S3:

1. **Optional — live data:** sync raw captures from S3 (set bucket and optional prefix; defaults match `weather-study`):

```bash
uv run --package weather-study-cli weather-study sync-s3 --bucket "<WEATHER_STUDY_BUCKET>" --prefix raw
```

2. **Rebuild SQLite from the raw tree** (after S3 sync, `--input` should match `--output-root` from step 1, default `.study/raw-s3`; for bundled mock data only, use the package path below):

```bash
uv run --package weather-study-cli weather-study ingest-raw --reset --input .study/raw-s3
```

Bundled mock captures only (no S3):

```bash
uv run --package weather-study-cli weather-study ingest-raw --reset --input packages/weather-study-cli/mock-data/raw
```

3. **Print per-city counts** of local dates with no missing expected hourly captures (same rules as `report-gaps`):

```bash
uv run --package weather-study-cli weather-study count-valid-study-days
```

For machine-readable output:

```bash
uv run --package weather-study-cli weather-study count-valid-study-days --format json
```

## What the user gets

Text lines like `Seattle: 6` or `San Francisco (no captures): 0`—one row per configured study city in fixed order.

## Notes

- **Completeness** here means full expected city-hour coverage for each local date (completed days expect hours 0–23; the current local date uses a partial window). This is **not** the same as the chart/UI `valid_day_count` inside `compute-accuracy-metrics` (which applies spec eligibility, censoring, and market resolution).
- Default DB path is `.study/weather-study.db` under the repo root.
- If step 1 is skipped, use `packages/weather-study-cli/mock-data/raw` or another local raw tree for `--input` instead of `.study/raw-s3`.
