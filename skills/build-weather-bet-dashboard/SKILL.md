---
name: build-weather-bet-dashboard
description: Build or refresh the repo's multi-city weather betting dashboard by coordinating the installed `weather`, `kalshi-weather-markets`, and `weather-dashboard` CLIs. Use when Codex needs to pull live data for the cities listed in `cities.txt`, normalize forecast hours plus Kalshi ladders into the dashboard schema, and produce fresh `dashboard.json` plus the local app command for review or live use.
---

# Build Weather Bet Dashboard

## Overview

Generate the validated six-city dashboard workflow without re-deriving the data plumbing each time. Use the bundled script to pull weather and market data, write raw JSON artifacts, build the normalized payload, optionally export HTML, and then run the local dashboard server.

## Quick Start

1. Run `scripts/build_dashboard.py`.
2. Return the generated `dashboard.json` path and the `weather-dashboard serve --input ...` command.
3. Run the local dashboard server when the user wants the interactive UI.
4. Mention the optional exported HTML path when relevant, but do not treat it as the main artifact.

Example commands:

```bash
python /abs/path/to/skills/build-weather-bet-dashboard/scripts/build_dashboard.py
python /abs/path/to/skills/build-weather-bet-dashboard/scripts/build_dashboard.py --output-dir /tmp/weather-dashboard
python /abs/path/to/skills/build-weather-bet-dashboard/scripts/build_dashboard.py --city Seattle --city Denver
```

## Workflow

### 1. Gather the city list

- Read the repo `cities.txt`.
- Treat the first non-empty line in each 3-line block as the city name.
- Preserve that file order unless the user asks for a subset.
- Let the bundled script map each supported city to the strict `weather` place string, such as `Seattle,WA`.

### 2. Pull weather data

- Run `weather "<city,state>" --range next-24h --format json`.
- Keep only forecast periods whose `start` is later than `range.start` and still falls on that city's local calendar date.
- Map each retained row to `start`, `end`, `temperature_f`, `summary`, `precipitation_probability_pct`, and `wind_speed`.

### 3. Pull market data

- Run `kalshi-weather-markets "<city>" --format json`.
- Keep the full active ladder for the selected daily event. Do not filter rows.
- Map each market row to `label`, `last_price_cents`, `yes_bid_cents`, `yes_ask_cents`, `no_bid_cents`, `no_ask_cents`, `selected_yes`, and `selected_no`.

### 4. Build the dashboard payload

- Write raw per-city CLI responses for traceability.
- Build `dashboard.json` with:
  - `schema_version: "1"`
  - `dashboard_date` from the first city's local date
  - `generated_at` in UTC
  - `cards` populated from the normalized weather and market data
- Use the bundled script for this step instead of rebuilding the JSON transformation inline.

### 5. Start the local UI

- Run `weather-dashboard serve --input <dashboard.json>`.
- Report the local URL and keep the process running while the user makes selections.
- The server writes into the local SQLite journal automatically when the user clicks Record.

### 6. Optional HTML export

- Use `weather-dashboard export-html` only when the user explicitly wants a standalone file export.
- Do not add Playwright or browser-validation steps unless the user explicitly asks for them.

## Bundled Script

Use `scripts/build_dashboard.py` for the actual orchestration. It:

- verifies `weather`, `kalshi-weather-markets`, and `weather-dashboard` are on `PATH`
- reads the repo `cities.txt`
- supports `--city` to build only a subset
- writes raw responses into `<output-dir>/raw/`
- writes `<output-dir>/dashboard.json`
- writes `<output-dir>/dashboard.html` as a secondary artifact
- prints a JSON summary with the output paths, included cities, and the `weather-dashboard serve` command

Default output directory:

```text
<repo>/.artifacts/latest-dashboard
```

## Output Expectations

- Return the absolute paths to the generated HTML and JSON.
- Return the dashboard serve command.
- Mention which cities were included.
- Mention whether the local dashboard server is running when relevant.
- If a requested city is missing from the built-in mapping, stop and update `scripts/build_dashboard.py` rather than guessing the `weather` place string.
