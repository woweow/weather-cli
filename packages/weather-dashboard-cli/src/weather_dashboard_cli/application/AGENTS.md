Purpose: dashboard-level orchestration above raw HTTP and UI rendering.

Rules:

- Own loading normalized dashboard snapshots and export behavior.
- The snapshot shape is owned by `weather-bets`; consume it here, do not redefine it.
- Keep persistence rules in `weather-bets`, not here.
