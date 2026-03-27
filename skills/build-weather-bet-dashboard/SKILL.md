---
name: build-weather-bet-dashboard
description: Build or refresh the repo's multi-city weather betting dashboard by coordinating the installed `weather`, `kalshi-weather-markets`, and `weather-dashboard` CLIs. Use when Codex needs to pull live data for the cities listed in `cities.txt`, normalize forecast hours plus Kalshi ladders into the dashboard schema, and generate fresh `dashboard.json` and `dashboard.html` output for review or local use.
---

# Build Weather Bet Dashboard

## Overview

Generate the validated six-city dashboard workflow without re-deriving the data plumbing each time. Use the bundled script to pull weather and market data, write raw JSON artifacts, build the normalized payload, and render the final HTML.

## Quick Start

1. Run `scripts/build_dashboard.py`.
2. Return the generated `dashboard.html` and `dashboard.json` paths.
3. Tell the user to open the HTML file directly, or run a simple static file server if they want a local URL.
4. Run `weather-dashboard serve-bets` only if the user wants the `Record bets` button to persist selections.

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

### 5. Render HTML

- Run `weather-dashboard generate-html --input <dashboard.json> --output <dashboard.html>`.
- Keep the default save endpoint unless the user explicitly wants a different host or port.
- Tell the user where the HTML file lives after generation.

### 6. Handle optional persistence

- Only run `weather-dashboard serve-bets` if the user wants the `Record bets` button to persist selections.
- Do not add Playwright or browser-validation steps unless the user explicitly asks for them.

## Bundled Script

Use `scripts/build_dashboard.py` for the actual orchestration. It:

- verifies `weather`, `kalshi-weather-markets`, and `weather-dashboard` are on `PATH`
- reads the repo `cities.txt`
- supports `--city` to build only a subset
- writes raw responses into `<output-dir>/raw/`
- writes `<output-dir>/dashboard.json`
- writes `<output-dir>/dashboard.html`
- prints a JSON summary with the output paths and included cities

Default output directory:

```text
<repo>/.artifacts/latest-dashboard
```

## Output Expectations

- Return the absolute paths to the generated HTML and JSON.
- Mention which cities were included.
- Mention whether the save server is running when relevant.
- If a requested city is missing from the built-in mapping, stop and update `scripts/build_dashboard.py` rather than guessing the `weather` place string.
