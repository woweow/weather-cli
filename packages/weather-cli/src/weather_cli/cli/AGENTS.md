Purpose: the `weather` command-line surface.

Rules:

- Own argparse, help text, and output formatting.
- Help text should stay explicit about supported ranges and JSON output so orchestration layers can rely on it.
- Call into application/adapters; do not add NOAA logic directly here.
