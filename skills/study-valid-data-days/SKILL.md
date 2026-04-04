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
2. Run **Execution block A** below from the repo root in order (S3 sync, then ingest, then count). Bucket defaults to the live collector config; override with env vars as documented.
3. Reply with **only** the stdout of step 3 (`count-valid-study-days`), unless step 1 or 2 fails—in that case paste the failing command’s stderr/stdout so the user can fix credentials or bucket access.
4. Do **not** recompute counts, infer numbers from files, or substitute mock data unless the user explicitly asked for offline/mock mode (see **Offline fallback**).

## Execution block A — live data (default)

Bucket: use `WEATHER_STUDY_BUCKET` when set and non-empty. Otherwise use the repo’s live collector bucket (same value as `aws/weather-study-collector/config/dev-live.json`): **`weather-study-raw-084375548651-us-west-2`**. Override the env var if you ever point the study at a different bucket.

Prefix: use `WEATHER_STUDY_PREFIX` if set and non-empty; otherwise use `raw` (matches `dev-live.json`).

AWS profile for `sync-s3`: use `WEATHER_STUDY_AWS_PROFILE` when set and non-empty (e.g. `dev` per `dev-live.json`). Otherwise use **`--profile ""`** so the AWS CLI uses the default credential chain (typical for access keys in CI).

```bash
export PATH="$HOME/.local/bin:$PATH"
BUCKET="${WEATHER_STUDY_BUCKET:-weather-study-raw-084375548651-us-west-2}"
if [ -n "${WEATHER_STUDY_AWS_PROFILE:-}" ]; then
  PROFILE_ARGS=(--profile "$WEATHER_STUDY_AWS_PROFILE")
else
  PROFILE_ARGS=(--profile "")
fi
uv run --package weather-study-cli weather-study sync-s3 \
  --bucket "$BUCKET" \
  --prefix "${WEATHER_STUDY_PREFIX:-raw}" \
  "${PROFILE_ARGS[@]}"
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
