Purpose: the local weather-market study package.

Rules:

- Own the raw study capture contract, mock data, loader/validator logic, and future ingest/analytics/visualization for the PRD study.
- Do not depend on `weather-bets` or `weather-dashboard-cli`.
- Use existing adapter CLIs/packages as upstream inputs rather than reimplementing NOAA or Kalshi fetching here.
