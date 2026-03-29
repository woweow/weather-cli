Purpose: the `weather-bets-sync` command-line surface.

Rules:

- Own argparse, help text, and JSON output.
- Help text should explain that provider settlement is authoritative and NOAA enrichment is supplemental.
- Call application-layer reconciliation functions; do not embed provider logic or SQL here.
