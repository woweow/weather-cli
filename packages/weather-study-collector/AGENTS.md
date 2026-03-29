Purpose: live raw capture assembly for the forecast-confidence study.

Rules:

- Own live weather and Kalshi capture orchestration only.
- Write schema-valid raw study files that `weather-study-cli` can validate and ingest unchanged.
- Keep SQLite ingest, derivations, and visualization out of this package.
- Treat weather and market fetches independently so one-side failures can still be persisted.
