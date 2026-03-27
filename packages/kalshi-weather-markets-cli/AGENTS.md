Purpose: fetch and normalize Kalshi daily high-temperature market ladders.

Owns:

- public Kalshi market-data adapter code
- market selection and sorting rules
- the `kalshi-weather-markets` CLI entrypoint

Does not own:

- dashboard rendering
- decision persistence
- weather fetching

Validation:

- Run `uv run pytest packages/kalshi-weather-markets-cli/tests -q`.
