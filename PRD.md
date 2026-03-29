# PRD: Weather Forecast Confidence and Market Opportunity Study

## Summary

Build a local-first analysis system with a cloud collector that captures hourly NOAA forecast snapshots and Kalshi market ladders for a fixed set of cities, stores raw snapshots in S3, ingests them into a local SQLite study database, and renders city-by-city visualizations showing when the forecast becomes reliable enough to matter for betting.

The purpose is not to create another decision journal. The purpose is to answer questions like:

- For Seattle, at 10:00 a.m. local time, how often did the forecast already identify the final daily high correctly?
- By what hour does each city usually become trustworthy?
- At the time the forecast becomes trustworthy, had the Kalshi market already priced that information in?

## Product Goal

The end state is a workflow where:

1. A cloud collector runs every hour without depending on a laptop being awake.
2. Each run stores immutable raw data for the supported cities.
3. A local ingest step can pull down those raw files and build a study database.
4. A local visualization can show forecast-confidence curves by city.
5. The same visualization can later show whether a forecast edge still existed relative to the market at the same time.

This project is for local research and decision support, not for a production SaaS system.

## Core Questions To Answer

- For each city and local hour, what percentage of observed days had the correct final daily high identified at that hour?
- For each city and local hour, how many valid study days contributed to that percentage?
- When does the confidence curve become practically useful, such as 60%, 70%, 80%, or 90%?
- Did the Kalshi ladder at that same hour still leave room for an edge, or had the market already converged?

## Scope

### In Scope

- Hourly raw capture of NOAA remaining-day forecast snapshots
- Hourly raw capture of Kalshi daily temperature market ladders
- Immutable storage of raw capture files in S3
- Local ingest into SQLite
- Local derivation of actual daily highs from NOAA observations
- City-by-city visualization of hourly forecast accuracy
- Missing-data-aware analytics
- Mock raw data that unblocks ingest and visualization before live data exists

### Out of Scope

- Cloud-hosted dashboards
- Multi-user access
- Production-grade monitoring
- Broad automated test coverage
- Historical reconstruction of past intraday NOAA forecasts through the current `weather-cli` point-forecast path

## Success Criteria

The first complete milestone is achieved when:

1. The cloud collector writes raw hourly files to S3 on schedule.
2. A checked-in mock raw dataset exists and can be uploaded to S3 or ingested locally.
3. The ingest pipeline can build a local SQLite study database from either mock or real raw files.
4. The visualization can render at least one city chart from mock data.
5. After one to two weeks of live collection, the same visualization works against real data with no schema changes.

## Users

Primary user:

- One local operator using the system to study forecast reliability and betting timing

Secondary user:

- An implementation agent that needs a clear roadmap and data contracts

## Design Principles

- Capture raw data first and derive analytics later.
- Prefer immutable append-only raw files over updating objects in place.
- Keep cloud collection simple and cheap.
- Keep analysis local and easy to inspect.
- Make missing data explicit instead of hiding it.
- Optimize for practical decision support, not academic purity.
- Prefer replacement over migration if the study schema changes materially.

## High-Level Architecture

### Component 1: Cloud Collector

Recommended architecture:

- `EventBridge Scheduler` triggers an hourly AWS Lambda.
- The Lambda fetches weather forecast snapshots and Kalshi ladder snapshots for the configured cities.
- The Lambda writes raw JSON objects to S3.

Why this architecture:

- It removes dependency on a laptop being open.
- It keeps storage cheap and simple.
- It gives a clean handoff boundary between collection and analysis.

### Component 2: Local Ingest and Derivation

- A local package pulls raw files from S3 using the AWS CLI or SDK with the AWS dev profile.
- It validates raw payload shape.
- It stores normalized study rows in SQLite.
- It computes actual daily highs from NOAA observations after the day is complete.
- It derives analytics tables and materialized summaries used by visualization.

### Component 3: Local Visualization

- A local visualization reads the SQLite study database.
- It renders city-by-city charts of forecast accuracy by local hour.
- It surfaces coverage counts and missing-data warnings alongside accuracy.
- It later adds market-opportunity overlays using the captured Kalshi data.

## Why S3 Instead Of A Cloud Database

Default choice:

- Use S3 for raw capture storage.

Reasons:

- Raw append-only snapshots are a natural fit for object storage.
- It avoids early schema lock-in in a managed database.
- It is cheaper and simpler than introducing RDS for this project.
- It supports replay if ingest logic changes.

Non-default choice:

- Do not introduce RDS, DynamoDB, or another managed database in phase 1 unless a concrete need appears.

## Scheduling Strategy

Default strategy:

- Run the collector every hour.

Collection window:

- Start with all hours enabled for simplicity and data completeness.
- If desired later, add per-city local-hour filtering in the collector configuration.
- Avoid encoding fragile timezone assumptions in EventBridge schedules.

Failure behavior:

- If a given run fails for one city, persist successful city captures for the others.
- Missing runs are acceptable; the analytics layer must handle them explicitly.

## Supported Cities

Initial target set:

- Seattle, WA
- San Francisco, CA
- Los Angeles, CA
- Las Vegas, NV
- Phoenix, AZ
- Denver, CO

The collector configuration should define cities centrally so both cloud capture and local analysis use the same list.

## Data Capture Contract

The raw capture format is the contract that unblocks parallel work. It must be defined before implementation of live collection, ingest, or visualization.

Recommended raw object granularity:

- One S3 object per city per capture time

Reasons:

- Partial failures do not lose the whole hourly run.
- Retry and deduplication are simpler.
- Ingest can be incremental.

Recommended S3 key shape:

```text
raw/study_version=1/city=Seattle/state=WA/local_date=2026-03-29/local_hour=10/captured_at_utc=2026-03-29T17-00-00Z.json
```

Each raw object should include:

```json
{
  "schema_version": "1",
  "captured_at_utc": "2026-03-29T17:00:00Z",
  "collector": {
    "name": "weather-market-study-lambda",
    "version": "1"
  },
  "city": {
    "name": "Seattle",
    "state": "WA",
    "place": "Seattle,WA",
    "timezone": "America/Los_Angeles"
  },
  "capture_context": {
    "local_timestamp": "2026-03-29T10:00:00-07:00",
    "local_date": "2026-03-29",
    "local_hour": 10
  },
  "weather": {
    "source": "weather-cli rest-of-today",
    "payload": {}
  },
  "market": {
    "source": "kalshi-weather-markets --format json",
    "payload": {}
  },
  "errors": []
}
```

Rules:

- `weather.payload` should preserve the raw normalized output from `weather-cli`.
- `market.payload` should preserve the raw normalized output from `kalshi-weather-markets-cli`.
- If one source fails and the other succeeds, still write the object with the successful payload and an `errors` entry.
- Do not discard source metadata needed for replay or debugging.

## Source Integration Notes

Weather source:

- Use `weather-cli` as the NOAA adapter.
- The collector should capture the remaining local-day forecast shape aligned to the existing `rest-of-today` behavior.

Market source:

- Use `kalshi-weather-markets-cli` as the Kalshi ladder adapter.
- The current ladder fetch path uses public market-data endpoints, so phase 1 should not require embedding Kalshi secrets into the collector.
- If a future authenticated Kalshi path is needed, reference environment variable names and deployment config, not hard-coded secrets.

## Local Study Database

Use a dedicated SQLite database for this study. Do not mix this data into `.bets/bets.db`.

Recommended database responsibilities:

- store ingested raw capture metadata
- store normalized hourly forecast rows
- store normalized hourly market ladder rows
- store derived daily actual highs
- store derived analytics summaries

Recommended table families:

- `raw_captures`
- `forecast_periods`
- `market_rows`
- `daily_actuals`
- `hourly_accuracy_metrics`
- `hourly_market_opportunity_metrics`

This schema can evolve aggressively. If it becomes incompatible, reset and rebuild from raw S3 data rather than trying to preserve backwards compatibility.

## Analytics Model

### Primary Forecast Metric

For a given city, local date, and capture hour:

- Determine the forecasted highest temperature remaining in the day from the captured NOAA forecast payload.
- Compare that value against the actual final observed high for that local date.

Primary city chart:

- x-axis: local hour
- y-axis: percentage of valid study days where that hour's capture matched the final observed high

This chart may or may not slope upward. Do not hard-code assumptions about its shape.

### Coverage Metric

Every hourly accuracy point must also expose:

- valid day count
- missing day count
- excluded day count by reason if available

The visualization must make sparse data obvious. Accuracy without coverage is not sufficient.

### Missing Data Rules

Missing data is expected and acceptable.

Rules:

- If a city-day has no snapshot for a given local hour, exclude that day from that hour's denominator.
- If the actual observed high for a city-day cannot be derived yet, keep the day unresolved and exclude it from finalized accuracy metrics.
- If weather data exists but market data is missing, the forecast-confidence metric can still be computed.
- If market data exists but weather data is missing, the city-hour can still contribute to market completeness metrics but not forecast accuracy.

### Market Opportunity Metrics

Forecast accuracy alone is not enough. The captured market ladder should later support questions like:

- At the hour when the forecast was right, had the market already concentrated on the winning bucket?
- What was the quoted price or implied confidence on the bucket that ended up winning?
- Was there still meaningful disagreement between forecast confidence and market pricing?

Phase 1 can capture and store all market ladder rows without finalizing the full opportunity model.
Phase 2 should derive city-hour metrics that join forecast correctness with the corresponding ladder state.

## Visualization Requirements

The first visualization should be simple and local.

Required outputs:

- a city selector
- an hourly forecast-accuracy line chart
- coverage counts by hour
- a visible sample-size warning when coverage is thin

Strongly desired later:

- a second chart or overlay for market-opportunity timing
- drill-down for a single day showing what the forecast and market looked like at each captured hour
- a table of example days where confidence emerged early or late

The first acceptable implementation can be a lightweight local web page or exported HTML backed by SQLite-derived JSON.

## Mock Data Strategy

Do not wait for two weeks of live collection before building ingest and visualization.

Required approach:

1. Freeze the raw S3 object schema first.
2. Create a checked-in mock dataset that matches that schema.
3. Make ingest work against the mock dataset.
4. Make visualization work against the mock-derived SQLite database.
5. After that path is proven, wire in the live cloud collector.

The mock dataset should include:

- at least two cities
- multiple days
- missing hours
- at least one day where the forecast gets the final high right early
- at least one day where it gets corrected later
- corresponding market ladder payloads with varying levels of certainty

The mock dataset should live in the repo and be optionally uploadable to the dev S3 bucket for end-to-end validation.

## Testing Philosophy

This project is intentionally light on unit tests.

Rules:

- Do not pursue coverage for its own sake.
- Prefer a small number of targeted tests on critical transformations and schema validation.
- Prefer end-to-end validation using mock raw files, real SQLite ingest, and real visualization output.
- Prefer replayable fixture-driven checks over dense test suites.

Minimum expected automated testing:

- one or two schema-validation tests for raw capture ingestion
- one or two analytics-derivation tests for key correctness logic
- one end-to-end test or smoke path using mock data if practical

Manual validation is acceptable and expected for:

- S3 upload and retrieval
- Lambda wiring
- chart inspection
- ingest replay against real collected files

## Deployment and Environment

Cloud environment:

- AWS account using the dev profile for deployment and inspection
- S3 bucket for raw study objects
- EventBridge Scheduler rule
- Lambda function with packaged repo code

Local environment:

- SQLite database on the laptop
- local CLI or script for pulling raw files from S3
- local visualization runner

Environment variable rules:

- Do not hard-code secrets in code or docs.
- Prefer public market-data collection paths when available.
- If authenticated provider access is introduced later, configure it through deployment environment variables or AWS-managed secret references.

## Package and Repo Direction

Recommended repo additions:

- a new root `PRD.md` for product intent and roadmap
- a new package for study ingest, derivation, and visualization
- an AWS deployment directory or scripts for the collector
- checked-in mock raw study data

Suggested package ownership:

- source adapters remain in existing adapter packages
- the new study package owns raw-study schema validation, SQLite ingest, derivations, and visualization
- AWS collector code owns scheduling entrypoints and S3 writes only

The collector should use the existing adapter packages rather than reimplementing weather or market fetching logic.

## Phasing

### Phase 1

- define raw schema
- generate mock raw files
- implement local ingest into SQLite
- implement first city chart from mock data

### Phase 2

- implement Lambda collector
- deploy hourly collection to AWS
- prove S3 writes and local ingest from real files

### Phase 3

- derive actual daily highs from NOAA observations
- compute finalized forecast-confidence metrics from real data
- improve visualization for coverage and drill-downs

### Phase 4

- derive market-opportunity metrics
- compare forecast correctness against market pricing by hour
- identify windows where forecast confidence is strong but market certainty is still lagging

## Roadmap

The following tasks are intentionally written at a story level. They are not implementation subtasks.

1. Define the raw study object schema for one city-hour capture, including weather payload, market payload, metadata, and partial-failure behavior.
2. Choose the new study package layout and ownership boundaries so ingest, analytics, and visualization live outside `weather-bets` and `weather-dashboard-cli`.
3. Create a checked-in mock raw dataset that covers multiple cities, multiple days, and several missing-data scenarios.
4. Build a local raw-file loader that can read the mock dataset and the future S3 download set through the same code path.
5. Design and implement the dedicated SQLite study schema for raw capture metadata, normalized rows, daily actuals, and derived hourly metrics.
6. Implement the first ingest pipeline that converts raw study files into normalized SQLite rows and can be rerun safely.
7. Implement daily actual-high derivation so completed city-days can be resolved from NOAA observations after the fact.
8. Implement the first forecast-confidence metric set, including hourly correctness percentages and explicit coverage counts.
9. Build the first local visualization that renders a city selector, hourly accuracy chart, and coverage indicators from SQLite-derived data.
10. Add drill-down views or exports that let a user inspect a single city-day across captured hours when a chart point looks surprising.
11. Build the AWS collector packaging and deployment path for Lambda, EventBridge Scheduler, and S3 using the dev AWS profile.
12. Implement the live collector so it captures weather and market data independently and writes one raw object per city-hour to S3.
13. Prove end-to-end parity by uploading or generating mock raw files in S3 and running the same ingest path used for real files.
14. Add operational visibility for collection gaps so missing city-hours can be seen during ingest and surfaced in analytics.
15. Extend the analytics model to join forecast correctness with the captured market ladder and quantify whether an edge still existed at each hour.
16. Build a market-opportunity visualization that shows not just when the forecast was right, but whether the market had already converged.
17. Run the system live for at least one to two weeks, ingest the real S3 dataset locally, and validate that no schema changes are required to use the real data.
18. Refine metrics, charts, and capture windows only after live data reveals what is actually useful rather than what seemed useful in advance.

## Implementation Guidance For Agents

If an implementation agent is working from this PRD:

- do not start by writing a large test suite
- do not wire this into `weather-bets`
- do not block ingest or visualization on live data collection
- freeze the raw schema early
- use mock data to unblock downstream work
- keep raw capture immutable
- keep the study database resettable and reproducible from raw files

