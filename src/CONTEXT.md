# Source Code

The application codebase: a FastAPI backend and a Svelte (PWA) frontend.

## Structure

```
src/
├── backend/                  — FastAPI app (owns ALL business logic)
│   ├── api/                  — Route handlers / endpoints (thin)
│   ├── services/             — Business logic — the spine. Logic lives HERE.
│   ├── models/               — SQLAlchemy ORM models
│   ├── schemas/              — Pydantic request/response schemas
│   ├── core/                 — db session, deps, config, auth, security
│   ├── adapters/             — Per-bank CSV adapters (bank_a, bank_b)
│   ├── migrations/           — Alembic (versions/ + env.py)
│   └── tests/                — Pytest (mirrors source tree)
└── frontend/                 — Svelte PWA
    └── src/
        ├── routes/           — Pages (swipe panels + tab/dot nav)
        ├── lib/api/          — API client modules (one per resource)
        ├── lib/components/   — Shared UI components
        └── lib/stores/       — Svelte stores for shared state
```

## Patterns we follow

- **Own the spine, supervise the surface.** Schema, import, dedupe, and flagging are
  written and understood deliberately. Presentation leans on Claude. The parts that
  fail *invisibly* (import integrity, dedupe, flagging) get the most scrutiny.
- **Thin routers, fat services.** Routers validate/authorize and delegate; all
  business logic is in `services/`. Do not put `db.query`/`db.commit` logic in a
  route handler. (This is the one place we diverge from zircon's no-service pattern.)
- **Money is `Decimal`/`numeric`, never float.** Sign convention: negative = money out.
- **Every write is audited.** Imports and flag approvals write an `audit_log` entry
  (chain of custody) — provenance, not access control.
- **Idempotent import.** The `transactions` dedupe key — composite `UNIQUE (account_id,
  txn_date, amount, description_raw, balance)` — is the keystone. Re-importing the same
  file must add zero rows.
- Reads gate on an authenticated session; all family members have equal full access.
- Error handling: never surface a raw stack trace to a family member — friendly
  messages at the API boundary, full detail in logs.

## Patterns we avoid

- Float for money. Logic in routers. Secrets in code. Silent failure on import —
  prefer a loud, audited reject over a quiet wrong insert.

## Testing requirements

- The dangerous logic (Phase 1 schema constraints, Phase 2 import/dedupe/merchant
  normalisation, Phase 5 flagging) **must** have tests that prove behaviour with a
  real assertion — e.g. a duplicate insert is *actually rejected*, a re-import adds
  zero rows. A passing test, not a plausible-looking output.
- Backend: Pytest in `backend/tests/`, mirroring source; use shared conftest fixtures.
- Frontend: Vitest for component/logic; Playwright for the import + swipe e2e flows.
- Pure layout/config does not need tests; anything that can fail invisibly does.

## Environment

- Required env vars listed in `.env.example`. Never hardcode anything that belongs in
  an env var. `.env` is gitignored from commit one. Secrets never enter git.
