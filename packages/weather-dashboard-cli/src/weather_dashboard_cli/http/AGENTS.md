Purpose: browser-facing HTTP routes for the local dashboard app.

Rules:

- Own route wiring, status codes, and request/response handling.
- Call `weather-bets` application code for persistence.
- Keep UI rendering and DB details out of this layer.
