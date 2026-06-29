---
name: new-migration
description: Generate, review, and apply an Alembic migration for the finance app. Use when adding or modifying database tables (e.g. "generate a migration for X", "create a migration", "run migrations", "alembic revision"). Also invoked by scaffold-endpoint after a new model is registered.
---

# New Migration

Generates and validates an Alembic migration for the finance app's PostgreSQL schema.
The schema is the foundation everything stands on — review every generated migration
line by line.

## Setup reminder
All commands run from `src/backend/` with the venv active:
```bash
source src/backend/.venv/bin/activate
cd src/backend
```
The DB must be running (Postgres in Docker — see `ops/scripts/`).

## Steps

### 1. Verify the model is registered
Confirm the new/changed model is imported in `src/backend/models/__init__.py` and in
`__all__`. Alembic autogenerate only detects registered models — skipping this is the
most common reason a table silently never gets created.

### 2. Generate
```bash
./.venv/bin/alembic revision --autogenerate -m "<descriptive message>"
```
Message format: `<phase> <entity>` — e.g. `v1 accounts`, `v1 transactions`,
`v1 add flags`. Match the naming pattern already in `migrations/versions/`.

### 3. Review the generated file (the important step)
Open the new file in `src/backend/migrations/versions/`. Check:
- **upgrade()** adds exactly the expected tables/columns. Autogenerate is usually
  right but misses: **unique constraints, check constraints, and `server_default`s.**
- **The `transactions` dedupe key must be present** — composite `UNIQUE (account_id,
  txn_date, amount, description_raw, balance)`, the keystone of idempotent import.
  If autogenerate omitted it, add it by hand.
- **Money columns are `numeric`, never float/double.** Reject any `Float`.
- **Timestamps are `timestamptz`** (`DateTime(timezone=True)`).
- **downgrade()** reverses every change correctly.
- **No accidental drops** — autogenerate drops unregistered tables. An unexpected
  `op.drop_table` means a model isn't registered; stop and fix that, don't apply.

### 4. Apply
```bash
./.venv/bin/alembic upgrade head
```
If it fails, **fix forward** (edit the generated file) — don't delete-and-regenerate;
keep history clean.

### 5. Verify
```bash
./.venv/bin/alembic current   # should show the new revision as (head)
```
For the keystone tables, prove the constraint actually bites: insert a row, insert a
duplicate, confirm the second is **rejected** (psql or a pytest). Don't assume — this
is exactly the kind of thing that fails silently on financial data.

## Avoid
- `alembic downgrade base` against a DB with real family data without explicit sign-off.
- Editing an already-applied revision (e.g. the initial migration).
- Leaving a half-applied failed migration — fix forward or roll back intentionally.
