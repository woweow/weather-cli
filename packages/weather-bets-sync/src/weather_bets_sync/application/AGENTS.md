Purpose: provider reconciliation rules and orchestration above the raw provider/weather adapters.

Rules:

- Read unresolved bets through `weather-bets` application APIs.
- Fetch provider settlement data and NOAA observed highs here.
- Match by exact provider tickers, not by human-readable labels.
- Write settled outcomes back through `weather-bets`.
- Do not embed argparse or raw SQL in this layer.
