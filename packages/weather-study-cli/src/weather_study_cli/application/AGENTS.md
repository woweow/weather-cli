Purpose: study-domain logic above raw file I/O.

Rules:

- Own raw capture validation, path metadata checks, mock-data conventions, and future ingest/analytics logic.
- Keep CLI argument parsing and output formatting out of this layer.
- Keep NOAA and Kalshi fetch logic in the adapter packages.
