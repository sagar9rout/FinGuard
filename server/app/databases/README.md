# app/databases

Intentionally empty. PostgreSQL persistence is a separate, approved phase (see `backend/finguard_persistence` and
`docs/design/pr3-persistence-design.md`). This server opens no database connection and reads no database setting.
The browser must never connect to PostgreSQL directly.
