# Old Dataset Archive Runbook

How to move old live study captures out of the active `raw/` prefix without losing them, and how to fetch archived datasets later for analysis.

## Current clean-data cutover

Use this cutover for the March 2026 collector fix:

- Bucket: `weather-study-raw-084375548651-us-west-2`
- Active live prefix: `raw/`
- Archive prefix: `raw-pre-fix-2026-03-31/`
- Clean-data cutoff: `captured_at_utc < 2026-03-31T14-00-00Z`

Why this cutoff:

- The fixed collector was deployed on March 31, 2026 at about `2026-03-31T13:18:14Z`
- `2026-03-31T14:00:00Z` is the first scheduled top-of-hour capture after that deploy
- Everything before that belongs to the pre-fix startup dataset

## Prerequisites

```bash
aws sso login --profile dev
```

Set the shared variables once per shell:

```bash
export WEATHER_STUDY_BUCKET=weather-study-raw-084375548651-us-west-2
export WEATHER_STUDY_PROFILE=dev
export WEATHER_STUDY_LIVE_PREFIX=raw
export WEATHER_STUDY_ARCHIVE_PREFIX=raw-pre-fix-2026-03-31
export WEATHER_STUDY_CUTOFF=2026-03-31T14-00-00Z
export WEATHER_STUDY_MANIFEST=/tmp/weather-study-pre-fix-2026-03-31.txt
```

## Preview the keys to archive

Build a manifest of keys whose `captured_at_utc` is earlier than the clean cutoff:

```bash
aws s3api list-objects-v2 \
  --bucket "${WEATHER_STUDY_BUCKET}" \
  --prefix "${WEATHER_STUDY_LIVE_PREFIX}/" \
  --profile "${WEATHER_STUDY_PROFILE}" \
  --output json \
| jq -r --arg cutoff "${WEATHER_STUDY_CUTOFF}" '
    .Contents // []
    | map(.Key)[]
    | select((capture("captured_at_utc=(?<ts>[^.]+)\\.json").ts) < $cutoff)
  ' \
> "${WEATHER_STUDY_MANIFEST}"
```

Sanity-check the manifest before moving anything:

```bash
wc -l "${WEATHER_STUDY_MANIFEST}"
head -5 "${WEATHER_STUDY_MANIFEST}"
tail -5 "${WEATHER_STUDY_MANIFEST}"
```

## Move the old dataset into the archive prefix

This preserves the raw file structure under a different top-level prefix.

```bash
while IFS= read -r key; do
  aws s3 mv \
    "s3://${WEATHER_STUDY_BUCKET}/${key}" \
    "s3://${WEATHER_STUDY_BUCKET}/${WEATHER_STUDY_ARCHIVE_PREFIX}/${key#${WEATHER_STUDY_LIVE_PREFIX}/}" \
    --profile "${WEATHER_STUDY_PROFILE}"
done < "${WEATHER_STUDY_MANIFEST}"
```

## Verify the cutover

The live prefix should no longer contain any pre-cutoff objects:

```bash
aws s3api list-objects-v2 \
  --bucket "${WEATHER_STUDY_BUCKET}" \
  --prefix "${WEATHER_STUDY_LIVE_PREFIX}/" \
  --profile "${WEATHER_STUDY_PROFILE}" \
  --output json \
| jq -r --arg cutoff "${WEATHER_STUDY_CUTOFF}" '
    .Contents // []
    | map(.Key)[]
    | select((capture("captured_at_utc=(?<ts>[^.]+)\\.json").ts) < $cutoff)
  '
```

That command should print nothing.

Then rebuild the live report from the cleaned prefix:

```bash
uv run --package weather-study-cli weather-study build-report \
  --bucket "${WEATHER_STUDY_BUCKET}" \
  --prefix "${WEATHER_STUDY_LIVE_PREFIX}" \
  --sync-output-root /tmp/weather-study-live-raw \
  --db-path /tmp/weather-study-live.db \
  --output /tmp/weather-study-live.html \
  --format text
```

## Fetch an archived dataset later

To inspect or rebuild from the archived pre-fix dataset:

```bash
uv run --package weather-study-cli weather-study build-report \
  --bucket "${WEATHER_STUDY_BUCKET}" \
  --prefix "${WEATHER_STUDY_ARCHIVE_PREFIX}" \
  --sync-output-root /tmp/weather-study-archived-raw \
  --db-path /tmp/weather-study-archived.db \
  --output /tmp/weather-study-archived.html \
  --format text
```

Or if you only want the raw files locally:

```bash
uv run --package weather-study-cli weather-study sync-s3 \
  --bucket "${WEATHER_STUDY_BUCKET}" \
  --prefix "${WEATHER_STUDY_ARCHIVE_PREFIX}" \
  --output-root /tmp/weather-study-archived-raw \
  --format text
```

## Notes

- Use `s3api list-objects-v2` instead of `aws s3 ls` when filtering manifests, because the study keys contain spaces in city names such as `San Francisco`.
- Keep archived datasets under separate top-level prefixes. Do not mix them back into `raw/`.
- Prefer date-based archive names such as `raw-pre-fix-2026-03-31/` so cutovers are obvious from the prefix alone.
- For future cutovers, keep the same process: choose a UTC cutoff, build a manifest from `captured_at_utc`, move matching keys, then verify `raw/` only contains post-cutoff data.
