---
name: scaffold-endpoint
description: Scaffold a new finance-app backend resource — SQLAlchemy model, Pydantic schemas, a service module (business logic), and a thin FastAPI router — wired into the app and models registry, with an Alembic migration. Use when adding a new entity or REST resource to the backend (e.g. "add an accounts endpoint", "new transactions resource", "scaffold X table + CRUD").
---

# Scaffold Endpoint

Adds one backend resource end to end, matching this project's conventions.

> **This project keeps a real service layer.** Unlike a thin-router app, business
> logic lives in `src/backend/services/`, not in the route handler. Routers
> validate, authorize, and delegate; services do the work and own the DB session.
> This is deliberate — we own the spine. Do not collapse logic into the router.

## Canonical reference
Read the equivalent files for an existing resource and copy their shape before
writing anything. Use `accounts` as the reference: `src/backend/api/accounts.py`
(router), `src/backend/services/accounts.py` (service), `src/backend/models/account.py`
(model), `src/backend/schemas/accounts.py` (schemas).

## Confirm with the user before writing anything
1. **Resource name** — singular snake_case (`account`) and plural for the URL (`accounts`).
2. **Fields** — name, Python type, nullable. **Money fields are `Decimal`/`numeric`,
   never float.** Timestamps `timestamptz`.
3. **Relationships** — FKs (e.g. `account_id`, `category_id`, `merchant_id`).
4. **Audit** — does a write to this resource need an `audit_log` entry? (Imports and
   approvals always do.)

## Steps

### 1. Model — `src/backend/models/<name>.py`
- Inherit the shared base/mixins (surrogate PK, `created_at` as `timestamptz`).
- `__tablename__` = plural snake_case.
- SQLAlchemy 2.0 mapped style: `Mapped[...] = mapped_column(...)`.
- Money → `Numeric`; **never** `Float`. Unique/check constraints declared here (e.g.
  the `transactions` dedupe key — composite `UNIQUE (account_id, txn_date, amount, description_raw, balance)`).

### 2. Register the model — `src/backend/models/__init__.py`
Add the import and an entry in `__all__`. Alembic autogenerate only sees registered
models — do not skip this.

### 3. Schemas — `src/backend/schemas/<name>.py`
Purpose-specific Pydantic models shaped to what the endpoint actually returns or
accepts — not a generic Create/Update/Out triple. Look at `schemas/accounts.py` or
`schemas/spend.py` for the pattern: lean response models, `model_config =
ConfigDict(from_attributes=True)` where ORM objects are returned directly.

### 4. Service — `src/backend/services/<plural>.py`  ⭐ the spine
- The CRUD/business functions: `list_x`, `get_x`, `create_x`, `update_x`, `delete_x`,
  plus any domain logic for this resource.
- Services take the `Session` and typed inputs; they own `db.query` / `db.commit`.
- Where a write must be audited, the service writes the `audit_log` entry in the same
  transaction (provenance is part of the operation, not an afterthought).
- Keep money as `Decimal` end to end.

### 5. Router — `src/backend/api/<plural>.py` (thin)
- `router = APIRouter(tags=["<plural>"])`.
- Deps: `get_db`, current-session/user dependency. Reads and writes both require an
  authenticated session (family members have equal full access in v1).
- Routes delegate straight to the service:
  - `GET` list → 200 · `GET /{id}` → 200 / 404
  - `POST` → 201 · `PATCH /{id}` → 200, `body.model_dump(exclude_unset=True)`
  - `DELETE /{id}` → 204
- No `db.query`/`db.commit` here — call the service.

### 6. Wire into the app — `src/backend/main.py`
Add the import and `app.include_router(...)` in the existing block.

### 7. Migration
Hand off to the `new-migration` skill to generate, review, and apply.

### 8. Tests
Add `src/backend/tests/test_<plural>.py`. For dangerous resources (transactions,
flags, imports) prove behaviour with a real assertion — e.g. a duplicate dedupe-key
insert is actually rejected.

## Done looks like
The resource lists/creates/updates/deletes via the API, logic sits in the service,
the migration is applied, and `check` passes.
