# weather-cli workspace

This repo now contains multiple Python CLIs in a small `uv` workspace:

- `weather-cli`: NOAA observations and forecast windows
- `kalshi-weather-cli`: Kalshi daily high-temperature market snapshots
- `weather-dashboard-cli`: Static HTML dashboard generation and local bet recording

## Commands

```bash
uv run --package weather-cli weather "Seattle,WA" --range today
uv run --package kalshi-weather-cli kalshi-weather Seattle
uv run --package kalshi-weather-cli kalshi-weather --list-cities
uv run --package weather-dashboard-cli weather-dashboard generate-html --help
uv run --package weather-dashboard-cli weather-dashboard serve-bets --help
```

## Layout

```text
packages/
  weather-cli/
  kalshi-weather-cli/
  weather-dashboard-cli/
skills/
```

Each package owns its own `pyproject.toml`, source tree, and tests. The root `uv.lock` covers the workspace.
