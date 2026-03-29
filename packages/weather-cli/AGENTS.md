Purpose: fetch and normalize NOAA weather data for strict city/state inputs.

Owns:

- source adapters under `src/weather_cli/adapters`
- application rules under `src/weather_cli/application`, including exact local-day observed-high lookup
- the `weather` CLI entrypoint

Does not own:

- decision persistence
- dashboard rendering
- market data
- provider reconciliation

Validation:

- Run `uv run pytest packages/weather-cli/tests -q`.
