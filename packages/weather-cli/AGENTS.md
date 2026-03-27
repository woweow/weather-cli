Purpose: fetch and normalize NOAA weather data for strict city/state inputs.

Owns:

- source adapters under `src/weather_cli/adapters`
- application rules under `src/weather_cli/application`
- the `weather` CLI entrypoint

Does not own:

- decision persistence
- dashboard rendering
- market data

Validation:

- Run `uv run pytest packages/weather-cli/tests -q`.
