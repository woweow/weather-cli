Purpose: browser-facing HTTP routes for the local dashboard app.

Rules:

- Own route wiring, status codes, and request/response handling.
- Validate and forward the posted snapshot through `weather-bets` application code for persistence.
- Keep UI rendering and DB details out of this layer.
