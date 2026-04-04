---
name: study-valid-data-days
description: Summarize live (or local) weather-study raw captures—sync from S3 if needed, ingest, then count complete local days per city. Triggered by "summarize lambda data" / landed data / valid study days. Prefer live S3; do not fall back to mock data unless sync is impossible after fixing credentials.
---

# Study valid data days ("summarize lambda data")

## When this applies

Trigger phrases: **summarize lambda data**, **summarize landed data**, valid days of test data, complete capture days, data coverage per city, how much study data after S3 ingest.

## Credentials (read this first)

- **`weather-study sync-s3` does not pass `--profile` by default.** It runs plain `aws s3 sync`, which uses the **default AWS credential chain**: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN`, then optional `AWS_PROFILE` / `AWS_DEFAULT_REGION`, then shared config `[default]`, then instance role, etc.

### Cursor cloud agent vs local agent

Infer from context (e.g. Cursor Cloud / remote VM vs your own laptop). Rule of thumb:

- **If you are an agent running in the cloud** (Cursor Cloud, CI, or any environment where AWS is supplied via injected environment variables or an instance role): **do not use the `dev` profile.** Run `sync-s3` **without** `--profile` so `aws` picks up those credentials. A `dev` entry in `~/.aws` often does not exist and will error.
- **If you are an agent running locally** on a machine where you authenticate with a shared-credentials profile (the repo convention is `dev`): **use `--profile dev`** (or `export AWS_PROFILE=dev`) for `sync-s3` so the CLI uses that profile.

- **Generic cloud / CI with injected keys:** ensure `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION` (or `AWS_REGION`) are set. No `~/.aws` file is required.
- Optional sanity check (uses the same default chain as sync when no `--profile` is passed):

```bash
aws sts get-caller-identity
```

If that fails, fix credentials before running the study commands.

## Required inputs

- **`WEATHER_STUDY_BUCKET`**: S3 bucket containing Lambda collector output (example from repo docs: `weather-study-raw-084375548651-us-west-2`).
- **Prefix**: usually `raw` (matches the live collector). Pass `--prefix raw` explicitly if unsure.

## What to run (live path — always try this first)

From the repository root:

**1. Sync raw captures from S3**

```bash
uv run --package weather-study-cli weather-study sync-s3 --bucket "${WEATHER_STUDY_BUCKET}" --prefix raw
```

If (and only if) this environment uses a named AWS profile instead of env vars:

```bash
uv run --package weather-study-cli weather-study sync-s3 --bucket "${WEATHER_STUDY_BUCKET}" --prefix raw --profile dev
```

**2. Rebuild the study SQLite DB from the synced tree**

```bash
uv run --package weather-study-cli weather-study ingest-raw --reset --input .study/raw-s3
```

**3. Print per-city counts** of local dates with no missing expected hourly captures (same rules as `report-gaps`):

```bash
uv run --package weather-study-cli weather-study count-valid-study-days
```

JSON:

```bash
uv run --package weather-study-cli weather-study count-valid-study-days --format json
```

## Agent behavior

1. Run steps 1–3 in order. **Do not skip sync** when the user asked for landed/lambda data and credentials may be present.
2. If step 1 fails on credentials, state the error and **one** concrete fix (e.g. set the three env vars, or pass `--profile dev`). **Do not** silently switch to mock data.
3. Use bundled mock raw data **only** when the user explicitly wants offline/demo data, or when sync cannot succeed after credential fixes:

```bash
uv run --package weather-study-cli weather-study ingest-raw --reset --input packages/weather-study-cli/mock-data/raw
uv run --package weather-study-cli weather-study count-valid-study-days
```

## What the user gets

Text lines like `Seattle: 6` or `San Francisco (no captures): 0`—one row per configured study city in fixed order.

## Notes

- **Completeness** here means full expected city-hour coverage for each local date (completed days expect hours 0–23; the current local date uses a partial window). This is **not** the same as the chart/UI `valid_day_count` inside `compute-accuracy-metrics`.
- Default DB path is `.study/weather-study.db` under the repo root.
- Default sync download directory is `.study/raw-s3`.
