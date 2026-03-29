Purpose: the raw Kalshi public-market adapter layer.

Rules:

- Own HTTP request/response handling against Kalshi's public endpoints.
- Expose exact market/event lookup helpers that higher layers can reuse.
- Do not embed catalog rules, CLI formatting, or dashboard persistence here.
