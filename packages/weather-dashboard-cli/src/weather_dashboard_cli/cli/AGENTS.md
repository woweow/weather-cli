Purpose: the `weather-dashboard` command-line surface.

Rules:

- Own argparse and top-level command dispatch.
- Keep `--help` accurate about the provider-aware snapshot schema, browser routes, and save behavior.
- Do not embed request handling or persistence rules here.
