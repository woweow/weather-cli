---
name: study-valid-data-days
description: When the user says "summarize lambda data" (or asks for valid/complete study days per city), run a fixed three-command bash sequence from the repo root—S3 sync, ingest, count-valid-study-days—and paste the CLI output only. No manual counting, no extra analysis unless the user asks.
---

# Study valid data days (live Lambda / S3 pipeline)

## When this applies

Trigger phrase: **summarize lambda data**.

Also applies for: valid days of study data, complete capture days, data coverage per city, "how much lambda data", completeness before the study UI.

## Agent behavior (keep this deterministic)

1. Work from the **repository root** with `PATH` including `$HOME/.local/bin` (for `uv`).
2. Run **exactly** the three commands in **Execution block A** below, in order. Substitute only the bucket/prefix/profile as documented there.
3. Reply with **only** the stdout of step 3 (`count-valid-study-days`), unless step 1 or 2 fails—in that case paste the failing command’s stderr/stdout so the user can fix credentials or bucket access.
4. Do **not** recompute counts, infer numbers from files, or substitute mock data unless the user explicitly asked for offline/mock mode (see **Offline fallback**).

## Execution block A — live data (default)

Bucket: use environment variable `WEATHER_STUDY_BUCKET`. If it is unset or empty, stop and tell the user to set it (do not guess a bucket name).

Prefix: use `WEATHER_STUDY_PREFIX` if set and non-empty; otherwise use `raw`.

AWS credentials:

- If the environment uses **access keys** (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`), pass **`--profile ""`** on `sync-s3` so the AWS CLI uses the default credential chain (no named profile).
- If the user relies on a **named profile** (for example `dev` on a laptop), use `--profile dev` instead of `--profile ""`.

```bash
export PATH="$HOME/.local/bin:$PATH"
uv run --package weather-study-cli weather-study sync-s3 \
  --bucket "$WEATHER_STUDY_BUCKET" \
  --prefix "${WEATHER_STUDY_PREFIX:-raw}" \
  --profile ""
uv run --package weather-study-cli weather-study ingest-raw --reset --input .study/raw-s3
uv run --package weather-study-cli weather-study count-valid-study-days
```

Defaults aligned with the CLI: synced files land under **`.study/raw-s3`**; the study database is **`.study/weather-study.db`**. Step 2 must use the same `--input` path as step 1’s effective output root (the default `.study/raw-s3`).

Optional: for machine-readable output, run step 3 again with `--format json` **after** the text table, only if the user asked for JSON.

## What the user gets

The third command prints a **fixed-order table**, one line per configured study city, for example:

`Seattle: 7` and `San Francisco (no captures): 0` when that city has no raw captures after sync.

## Offline fallback (only when requested)

If the user explicitly wants **bundled mock data** (no S3, no AWS), skip step 1 and run:

```bash
export PATH="$HOME/.local/bin:$PATH"
uv run --package weather-study-cli weather-study ingest-raw --reset --input packages/weather-study-cli/mock-data/raw
uv run --package weather-study-cli weather-study count-valid-study-days
```

State clearly that the summary is from **mock captures**, not Lambda.

## Notes

- **Completeness** here means full expected city-hour coverage for each local date (completed days expect hours 0–23; the current local date uses a partial window). This is **not** the same as the chart/UI `valid_day_count` inside `compute-accuracy-metrics`.
- Cities with zero captures after sync usually mean the collector never wrote that city under the S3 prefix, not an ingest bug.
