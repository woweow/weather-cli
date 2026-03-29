Purpose: external integrations for geocoding, HTTP, and NOAA access.

Rules:

- Keep this layer focused on upstream request/response handling and adapter-side normalization.
- Keep it reusable for both the `weather` CLI and `weather-bets-sync`.
- Do not add argparse, terminal formatting, or persistence here.
