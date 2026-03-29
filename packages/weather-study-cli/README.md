# weather-study-cli

Local CLI for the forecast-confidence and market-opportunity study described in the root `PRD.md`.

Current scope:

- checked-in mock raw city-hour captures
- raw capture schema validation
- one local loader path that works for the bundled mock tree and future S3 downloads copied to disk

Examples:

```bash
uv run --package weather-study-cli weather-study validate-raw
uv run --package weather-study-cli weather-study validate-raw --input packages/weather-study-cli/mock-data/raw --format json
```

Notes:

- The raw capture contract keeps weather and market payloads separate and immutable.
- Files are stored with S3-style path metadata such as `study_version=1/city=Seattle/...`.
- Partial failures are valid as long as one source payload remains present and the missing source is recorded in `errors`.
- This package is the home for future SQLite ingest, derivations, and study visualization. It does not write to `.bets/bets.db`.
