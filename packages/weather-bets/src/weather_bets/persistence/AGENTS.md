Purpose: SQLite connections, migrations, and low-level repository queries.

Rules:

- Own schema changes and SQL.
- Prefer schema replacement over compatibility migrations.
- Keep write operations transactional.
- Do not embed CLI formatting or HTTP behavior here.
