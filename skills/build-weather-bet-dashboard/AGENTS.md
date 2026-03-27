Purpose: orchestrate the installed CLIs to produce a live dashboard session.

Rules:

- Use `weather` and `kalshi-weather-markets` to gather source data.
- Build `dashboard.json`, then launch `weather-dashboard serve --input <dashboard.json>`.
- Treat exported HTML as optional. The main artifact is the served local app.
- Do not bypass the CLI layer when an installed CLI already exposes the needed behavior.
