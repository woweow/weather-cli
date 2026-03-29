Purpose: SQLite schema, connection management, and persistence details for the study package.

Rules:

- Own only local SQLite concerns: schema creation, upserts, and normalized row storage.
- Keep raw file loading and CLI behavior out of this layer.
- Do not depend on `weather-bets`; this package owns its own resettable study database.
