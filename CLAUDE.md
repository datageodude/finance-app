# Finance App

A self-hosted, family-shared personal finance app. Weekly manual CSV imports (no
bank feeds). Privacy-first: financial data never touches the public internet or any
third-party infrastructure. Family members all have equal full-read access; every
action is audited (chain of custody).

Why this exists: [brief.md](brief.md) (the problem + success criteria). How the design
answers it: [planning/brief-to-solution.md](planning/brief-to-solution.md). The full
phased roadmap and schema deep-dive: [planning/PLAN.md](planning/PLAN.md) — read it
before building any phase.

## Tech Stack

- Language: Python (backend) / TypeScript (frontend)
- Frontend: Svelte — PWA, swipeable pages with persistent tab/dot nav
- Backend: FastAPI + SQLAlchemy — **holds all business logic** (own the spine)
- Database: PostgreSQL · migrations via Alembic · money is `numeric`, never float
- Auth: session-based, Argon2/bcrypt hashing, login rate-limit, MFA hooks (off in v1)
- Deploy: Docker Compose, self-hosted on a home device behind Tailscale
- CI/CD: TBD (decide at Phase 0)

## How to work here (read first)

The behavioural layer behind this map — read when working on the project:

- [identity.md](identity.md) — who you are on this project, and Geodude's "Best"
- [rules.md](rules.md) — the non-negotiable do/don'ts
- [examples.md](examples.md) — what good looks like (✅/❌ scenarios)
- [reference/](reference/) — domain glossary and agent-facing reference notes

## Workspaces

- /planning — Build roadmap (PLAN.md), feature specs, architecture docs, decisions
- /src — Application code (`src/backend/` + `src/frontend/`)
- /docs — API docs, user guides, changelog
- /ops — Deploy config (compose), monitoring, operational scripts

## Routing

| Task | Go to | Read | Skills |
|------|-------|------|--------|
| Understand the build plan | /planning | PLAN.md | — |
| Spec a feature | /planning/specs | CONTEXT.md | grilling |
| Record a decision | /planning/decisions | CONTEXT.md | domain-modeling |
| Write backend code | /src | CONTEXT.md | scaffold-endpoint, tdd |
| Write frontend code | /src | CONTEXT.md | scaffold-page |
| Change the schema | /src | CONTEXT.md | new-migration |
| Write docs | /docs | CONTEXT.md | — |
| Deploy or debug | /ops | CONTEXT.md | diagnosing-bugs |
| Verify the build passes | /src | CONTEXT.md | check |
| Outstanding tasks | TODO.md | — | — |

## Skills

Project-scoped skills live in `.claude/skills/`. Describe the task in plain language
and I'll route to the right one and say which I'm using.

| When you're… | Reach for |
|--------------|-----------|
| Adding a backend resource (model + schema + service + router) | `scaffold-endpoint` |
| Adding a frontend page (Svelte page + API client + route) | `scaffold-page` |
| Adding or changing a table | `new-migration` |
| Wrapping up / before a commit | `check` (lint + types + tests + build) |

The Matt Pocock skills (`tdd`, `grilling`, `domain-modeling`, `diagnosing-bugs`, …)
are available project-wide from the repo root.

### Stage gates — run these before proceeding (not optional)

This project gates each stage on the right skill. **Run the gate, surface the output,
and only then proceed.** Don't skip a gate because a step "looks simple" — the
dangerous logic here fails silently. If a gate finds nothing, say so and move on.

| Stage | Before you proceed, run | Why |
|-------|-------------------------|-----|
| **Planning / re-planning a phase** | `grilling` on the phase plan, then `to-prd` / `to-issues` to capture it | Stress-test assumptions before any code; this is the 🛑 checkpoint re-plan |
| **Designing schema or a new resource** | `domain-modeling` (terms + decision record), then `codebase-design` (module seams) | Phase 1 foundation + every new entity — expensive to change later |
| **Building** | `tdd` (test-first) — **mandatory on the dangerous phases (1 schema, 2 import, 5 flagging)** | Prove behaviour with a real assertion, not a plausible output |
| **Something's broken** | `diagnosing-bugs` | Structured diagnosis over guess-and-check |
| **Closing a phase / before commit** | `check` (lint + types + tests + build) | The "done when" bar isn't met until this is green |

These run *frequently and routinely* — at every phase boundary, every new resource,
every commit — not just once. The PLAN.md checkpoint protocol names the same gates at
each 🛑.

## Conventions

- Backend: routes in `src/backend/api/`, **logic in `src/backend/services/`**, ORM
  models in `src/backend/models/`, Pydantic schemas in `src/backend/schemas/`
- Frontend: API clients in `src/frontend/src/lib/api/`, pages in
  `src/frontend/src/routes/`; Svelte functional components only
- Naming: snake_case Python · camelCase TS functions · PascalCase Svelte components ·
  kebab-case files
- Money is always `numeric`/`Decimal`, never float. Timestamps `timestamptz` (UTC).
- Sign convention: negative = money out (locked everywhere — see PLAN open items)
- Testing: Pytest (`tests/` mirrors source) · Vitest + Playwright (frontend)
- Commits: conventional commits (`feat:` `fix:` `docs:` `chore:` `test:`)
- Decision records: `planning/decisions/YYYY-MM-DD_title.md`

## Avoid

- Float for any monetary value — `numeric`/`Decimal` only.
- Business logic in routers — it belongs in `services/`. (This project deliberately
  keeps a real service layer; do not collapse logic into the route handlers.)
- Secrets in git — everything via `.env`, `.gitignore` from commit one.
- Building ahead of the current phase — honour the 🛑 checkpoints in PLAN.md.

## Current State

- Phase 0 complete (2026-06-27). Backend + frontend scaffolded; auth built and tested.
- Phase 1 complete (2026-06-28). Full schema built and tested: 9 model files, 3 services
  (`auditing`, `accounts`, `transactions`), 3 migrations (domains + lookups + seed,
  core entities, transactional), 12 schema tests all green including the keystone
  (duplicate insert actually rejected). `check` gate green.
- Phase 2 complete (2026-06-28). Import engine built and tested: `adapters/` (Bank A + Bank B),
  `services/seed.py`, `services/merchants.py`, `services/import_engine.py`, `schemas/imports.py`,
  `api/imports.py`. 40 new tests all green (4 seed + 21 adapter + 15 engine). `check` gate green.
- Phase 3 complete (2026-06-29). Import UX built: drag-drop + per-file preview cards + bulk confirm.
  Backend: `preview_import()` + `PreviewResult`, `/imports/preview`, `/imports/confirm`, `/imports/history`,
  `/accounts`. Frontend: `DropZone`, `ImportCard` (5-state machine), Import page, Import tab in nav.
  `check` gate green (61/61 tests, svelte-check 0 errors, build clean).
- Phase 4 panels (Cash Reserves, Spend vs Budget, Loans) complete (2026-06-29). Frontend pages built;
  backend APIs and services in place. Migration 0007 adds budgets table. `check` gate green.
- Phase 4 Flagged panel + Phase 5 Flagging engine complete (2026-06-29). Gate cycle (grilling →
  domain-modeling → codebase-design) run first. Backend: `services/flagging.py` (3 rules: over_threshold,
  double_charge, new_merchant), `api/flags.py` (GET /flags, approve, dismiss, generate backfill),
  `schemas/flags.py`, migration 0008 (UNIQUE idempotency constraint + merchant_threshold_overrides table).
  Frontend: `FlagCard.svelte`, `routes/(app)/flagged/+page.svelte`. 23 new tests all green.
  `check` gate green (84/84 tests, svelte-check 0 errors, build clean).
- Phase 4 Forecast panel complete (2026-06-29). Gate cycle (grilling → domain-modeling →
  codebase-design) run in parallel chat. Backend: `services/forecast.py` (equity-view,
  3-month lookback, `ForecastHorizon` dataclass), `schemas/forecast.py`, `api/forecast.py`.
  Frontend: today header (Cash/Loans/Funds breakdown) + 3 horizon cards + warning banner + empty state.
  `check` gate green (84/84 tests, svelte-check 0 errors, build clean).
- **Next:** Phase 4 🛑 checkpoint — tune `FLAG_THRESHOLD` and `DOUBLE_CHARGE_DAYS` against real data,
  then Phase 6 Categorisation refinement gate cycle. See [TODO.md](TODO.md).
- Outstanding tasks tracked in [TODO.md](TODO.md).
