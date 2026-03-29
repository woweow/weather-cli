Purpose: the `weather-bets` command-line surface.

Rules:

- Own argparse and JSON output.
- Document the clean-slate reset flow in `--help`.
- Keep the output contract explicit enough for another agent to consume without reading code.
- Do not embed SQL or snapshot validation rules directly here.
