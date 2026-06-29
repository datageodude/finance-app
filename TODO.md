# Finance App — TODO

Outstanding tasks. Phase detail lives in [planning/PLAN.md](planning/PLAN.md).

## Homework (blocks Phases 1–2)
- [x] Pull a transaction CSV from each bank — **template** samples for Bank A + Bank B
      added 2026-06-27 (`reference/bank_a.csv`, `reference/bank_b.csv`). Column shapes,
      date formats, time field, and sign conventions confirmed and written up in
      [reference/bank-csv-notes.md](reference/bank-csv-notes.md).
- [ ] Replace templates with **full real exports** before trusting edge cases (more rows
      = real amount spread for flag tuning; confirms the savings/loan account shapes too).

## Test data
- [x] Synthetic test corpus built (2026-06-27): `fixtures/generate.py` → 6 bank-format
      CSVs (5 accounts across both banks + all 4 account types, 3 months) + `seed/`
      accounts/categories/rules. Covers every feature + flag rule; catalogue with
      expected outcomes in [fixtures/README.md](fixtures/README.md).
- [x] **Phase 1:** write a seed loader that ingests `fixtures/seed/*.json` into the DB
      (accounts, categories, rules) — done 2026-06-28 (`services/seed.py`).
- [x] **Phase 2/5 (Phase 2 portion):** import dedupe assertions — idempotency (adds 0) and
      partial overlap (adds 2) both tested in `test_phase2_import.py`. Phase 5 flagging
      assertions deferred to Phase 5.
- [ ] **Phase 5:** turn the fixtures/README "expected outcomes" for flagging into actual
      test assertions (Dining is over budget, double-charge pairs, new-merchant flag).

## Open items from PLAN (resolve as you build)
- [x] Lock the sign convention everywhere — **negative = money out** (locked in schema +
      decision record 2026-06-28).
- [ ] Decide whether to seed categorisation from Bank B's `Category`/`Subcategory`
      (lean: suggestion only, keep our own categoriser authoritative across both banks).
- [ ] Draft the category starter list (Groceries, Fuel, Utilities, Insurance,
      Mortgage, Dining, Subscriptions, Medical, …) — seed migration needed.
- [x] Decide stored vs derived balance — **`opening_balance` (immutable) + cached
      `current_balance` + reconciliation check** (locked 2026-06-28, decision record).
- [ ] Decide the dedupe window for the double-charge flag (N days) — Phase 5 config.

## Phase 2 — Import engine ✅ (2026-06-28)
- [x] `adapters/__init__.py` — `ParsedRow`, `AdapterResult`, `BankAdapter` Protocol, `get_adapter()`
- [x] `adapters/bank_a.py` — `BankAAdapter` (preamble detection, POS prefix strip, internal-transfer detection)
- [x] `adapters/bank_b.py` — `BankBAdapter` (DD Mon YYYY dates, debit/credit split, Original Description)
- [x] `services/seed.py` — `load_fixtures(db, user_id)` from `fixtures/seed/*.json`
- [x] `services/merchants.py` — `get_or_create(db, normalised_name)`
- [x] `services/import_engine.py` — `run_import()` full pipeline + `ImportResult` + `ImportValidationError`
- [x] `schemas/imports.py` — `ImportResponse`, `ImportErrorResponse`
- [x] `api/imports.py` — `POST /api/imports` wired into `main.py`
- [x] 40 tests: 4 seed + 21 adapter (unit, no DB) + 15 engine (integration, real Postgres)
- [x] `check` gate green (lint clean, 61/61 tests pass, svelte-check 0 errors, build clean)
- [x] `credit_limit` added to `fixtures/seed/accounts.json` b3 entry
- [x] `db_with_lookups` fixture added to `conftest.py` for Phase 2+ tests

### Phase 2 🛑 checkpoint — what to do next (start of new chat)
- [x] Run `grilling` on the Phase 3 plan (drag-drop UI + account selector dropdown) — complete 2026-06-29
- [x] Run `domain-modeling` on Phase 3 — 2 ADRs written ([planning/decisions/2026-06-29_phase-3-import-ux.md](planning/decisions/2026-06-29_phase-3-import-ux.md))
- [x] Run `codebase-design` on Phase 3 — 7 seam decisions locked ([planning/decisions/2026-06-29_phase-3-module-seams.md](planning/decisions/2026-06-29_phase-3-module-seams.md))

## Phase 3 — Import UX ✅ (2026-06-29)
- [x] `services/import_engine.py` — `preview_import()` + `PreviewResult`; `_parse_and_validate()` private helper; `account_id` override param added to `run_import()`
- [x] `schemas/imports.py` — `PreviewResponse`, `ImportHistoryItem` added
- [x] `schemas/accounts.py` — NEW: `AccountSummary`
- [x] `api/imports.py` — `POST /imports` renamed to `POST /imports/confirm`; `POST /imports/preview` added; `GET /imports/history` added
- [x] `api/accounts.py` — NEW: `GET /accounts` (thin wrapper over `accounts_svc.list_accounts()`)
- [x] `main.py` — accounts router registered
- [x] `lib/api/imports.ts` — NEW: `previewImport()`, `confirmImport()`, `getImportHistory()`
- [x] `lib/api/accounts.ts` — NEW: `getAccounts()`
- [x] `lib/components/DropZone.svelte` — NEW: drag-drop + file picker; emits `File[]`; CSV-only validation
- [x] `lib/components/ImportCard.svelte` — NEW: per-file state machine (loading → preview/error/needs_account → confirming → success); `confirmTrigger` counter pattern
- [x] `routes/(app)/import/+page.svelte` — NEW: Import page (DropZone + cards + bulk confirm button + history list)
- [x] `lib/components/TabNav.svelte` — Import tab added as leftmost entry
- [x] `check` gate green: ruff clean, 61/61 backend tests pass, svelte-check 0 errors, build clean

### Phase 3 🛑 checkpoint — what to do next (start of new chat)
- [x] Run `grilling` + `domain-modeling` + `codebase-design` on Phase 4 Cash Reserves — complete 2026-06-29
      ([decisions/2026-06-29_phase-4-cash-reserves.md](planning/decisions/2026-06-29_phase-4-cash-reserves.md),
       [decisions/2026-06-29_phase-4-module-seams.md](planning/decisions/2026-06-29_phase-4-module-seams.md))
- [x] Run `grilling` + `domain-modeling` + `codebase-design` on Phase 4 Spend vs Budget — complete 2026-06-29
      ([decisions/2026-06-29_phase-4-spend-vs-budget.md](planning/decisions/2026-06-29_phase-4-spend-vs-budget.md),
       [decisions/2026-06-29_phase-4-spend-vs-budget-module-seams.md](planning/decisions/2026-06-29_phase-4-spend-vs-budget-module-seams.md))
- [x] Run `grilling` + `domain-modeling` + `codebase-design` on Phase 4 Flagged + Phase 5 Flagging engine — complete 2026-06-29
      ([decisions/2026-06-29_phase-5-flagging-engine.md](planning/decisions/2026-06-29_phase-5-flagging-engine.md),
       [decisions/2026-06-29_phase-5-module-seams.md](planning/decisions/2026-06-29_phase-5-module-seams.md))

### Phase 4 Flagged panel + Phase 5 Flagging engine ✅ (2026-06-29)
- [x] Gate cycle: `grilling` (13 decisions) → `domain-modeling` (5 new terms, 3 ADRs) → `codebase-design` (9 seam decisions)
- [x] Migration `0008_v1_flagging` — UNIQUE `(transaction_id, flag_type)` on flags + `merchant_threshold_overrides` table
- [x] `models/flag.py` — UNIQUE `__table_args__` added (for test `create_all`)
- [x] `models/merchant.py` — `MerchantThresholdOverride` model added
- [x] `models/__init__.py` — `MerchantThresholdOverride` registered
- [x] `services/flagging.py` — `run_for_import()`, `generate_for_account()`, `list_open_flags()`, `approve_flag()`, `dismiss_flag()` + 3 private rule checkers
- [x] `schemas/flags.py` — `FlagItem`, `ApproveRequest`, `FlagActionResponse`, `GenerateResponse`
- [x] `api/flags.py` — `GET /flags`, `POST /flags/{id}/approve`, `POST /flags/{id}/dismiss`, `POST /flags/generate`
- [x] `api/imports.py` — confirm endpoint wired to call `run_for_import()` after import commit
- [x] `main.py` — `flags_router` registered
- [x] `lib/api/flags.ts` — `FlagItem` interface + 4 fetch functions
- [x] `lib/components/FlagCard.svelte` — per-flag card with inline threshold input for over_threshold approve
- [x] `routes/(app)/flagged/+page.svelte` — replaced placeholder; live flag list with empty state
- [x] `tests/test_phase5_flagging.py` — 23 tests: all 3 rules + account-type filters + merchant overrides + idempotency + approve/dismiss + list_open_flags
- [x] `check` gate green: ruff clean, 84/84 tests, svelte-check 0 errors, build clean

### Phase 4 Flagged 🛑 checkpoint — what to do next
- [x] Forecast panel — gate cycle complete + built 2026-06-29 (decisions below)
- [x] Phase 4 🛑 threshold checkpoint — analysed 83 real fixture transactions 2026-06-29
      (25 over_threshold, 22 new_merchant, 2 double_charge). Finding: $100 is too noisy —
      flags regular groceries ($101–$110), utilities ($220), insurance ($130). Recommendation:
      **Option B** — raise `FLAG_THRESHOLD` to `300` **and** skip null-merchant transactions
      in `_check_over_threshold` (null-merchant = internal transfer, not discretionary spend).
      `DOUBLE_CHARGE_DAYS=7` is correct — keep. Implementation: 3-line guard in
      `services/flagging.py:_check_over_threshold` + update `FLAG_THRESHOLD` default in
      `flagging.py` + `.env.example`.
- [ ] Apply Option B threshold fix (`FLAG_THRESHOLD=300` + null-merchant guard)
- [ ] Phase 6 (Categorisation refinement) — run gate cycle before any code (deferred to new chat)

### Phase 4 Forecast panel ✅ (2026-06-29)
- [x] Gate cycle: `grilling` → `domain-modeling` → `codebase-design` — run in parallel chat 2026-06-29
      ([decisions/2026-06-29_phase-4-forecast.md](planning/decisions/2026-06-29_phase-4-forecast.md),
       [decisions/2026-06-29_phase-4-forecast-module-seams.md](planning/decisions/2026-06-29_phase-4-forecast-module-seams.md))
- [x] `services/forecast.py` — `get_forecast(db) → ForecastResult`; equity-view (all active accounts); 3-month lookback; `ForecastHorizon` dataclass
- [x] `schemas/forecast.py` — `ForecastHorizonSchema` + `ForecastResponse` (cash_total / loans_total / net_funds / horizons)
- [x] `api/forecast.py` — `GET /forecast` thin router (already registered in `main.py`)
- [x] `lib/api/forecast.ts` — `ForecastHorizon` + `ForecastData` interfaces + `getForecast()`
- [x] `routes/(app)/forecast/+page.svelte` — today header (Cash/Loans/Funds breakdown) + 3 side-by-side horizon cards (↑/↓ colour arrows) + warning banner + empty state + static footnote
- [x] `check` gate green: ruff clean, 84/84 tests, svelte-check 0 errors, build clean

### Phase 4 Spend vs Budget ✅ (2026-06-29)
- [x] Migration `0007_v1_budgets` — `budgets` table + UNIQUE `(category_id, valid_from)` + CHECK `(day=1)` + index
- [x] `models/budget.py` — `Budget` ORM model; registered in `models/__init__.py`
- [x] `services/seed.py` — `_load_categories(db, *, user_id)` now inserts `Budget` rows from `categories.json`
- [x] `services/spend.py` — `get_spend_summary(db)` → `SpendSummary`; rollforward, two-path inclusion, net-positive heuristic, sub-category rollup, uncategorised separate
- [x] `schemas/spend.py` — `CategorySpendRow` + `SpendSummary` Pydantic schemas
- [x] `api/spend.py` — `GET /spend/summary` router; registered in `main.py`
- [x] `lib/api/spend.ts` — `SpendSummary` TS interface + `getSpendSummary()` fetch function
- [x] `routes/(app)/spend/+page.svelte` — full panel: grand total, category rows, uncategorised pinned last, red-on-over-budget, no-data note
- [x] `check` gate green: ruff clean, 84/84 tests pass, svelte-check 0 errors, build clean

### Phase 4 Loans panel ✅ (2026-06-29)
- [x] Run `grilling` — 15 questions, all decisions locked
- [x] Run `domain-modeling` — 2 terms added to CONTEXT.md; 1 ADR ([planning/decisions/2026-06-29_phase-4-loans.md](planning/decisions/2026-06-29_phase-4-loans.md))
- [x] Run `codebase-design` — 7 seam decisions ([planning/decisions/2026-06-29_phase-4-loans-module-seams.md](planning/decisions/2026-06-29_phase-4-loans-module-seams.md))
- [x] Migration `0006_v1_loan_dates.py` — `loan_terms.start_date` + `loan_terms.end_date` (nullable date)
- [x] `models/account.py` — `LoanTerms.start_date` + `LoanTerms.end_date`
- [x] `services/accounts.py` — `list_loans()` (INNER JOIN terms, LEFT JOIN import, ORDER BY abs(balance) DESC)
- [x] `schemas/accounts.py` — `LoanDetail` with `balance_owing` (always positive)
- [x] `api/loans.py` — `GET /loans`; registered in `main.py`
- [x] `lib/api/loans.ts` — `LoanDetail` TS interface + `getLoans()`
- [x] `routes/(app)/loans/+page.svelte` — Total Owing headline, per-loan cards with progress bar, date range, redraw
- [x] `check` gate green (61/61 tests, svelte-check 0 errors, build clean)

## Phase 1 — Data model & schema ✅ (2026-06-28)
- [x] `core/types.py` — `MoneyAmount` (`numeric(14,2)`), `PercentageRate` (`numeric(6,4)`)
- [x] 9 model files: `lookups`, `account` (+`LoanTerms`/`CreditTerms`), `merchant`,
      `category`, `import_batch`, `transaction`, `rule`, `flag`, `audit_log`
- [x] 3 services: `auditing.record()`, `accounts.create_account()` (+`MissingSidecarError`),
      `transactions.reconcile()` + `recategorise()`
- [x] 3 migrations: `0002_v1_domains_and_lookups` (domains + 6 lookups + seed),
      `0003_v1_core_entities` (accounts, sidecars, merchants, categories),
      `0004_v1_transactional` (transactions dedupe UNIQUE, rules, flags, imports, audit_log)
- [x] 12 tests in `test_phase1_schema.py` — all pass, including keystone
      (duplicate insert actually rejected by UNIQUE constraint)
- [x] `check` gate green: lint (ruff) clean, 21/21 tests pass, svelte-check 0 errors, build clean
- [x] Decision records: `planning/decisions/2026-06-28_phase-1-schema.md` (18 decisions),
      `planning/decisions/2026-06-28_phase-1-module-seams.md` (6 seam decisions)
- [x] Glossary reconciled: "Fingerprint" → "Dedupe key" across all docs

### Phase 1 🛑 checkpoint — what to do next (start of new chat)
- [x] Re-plan Phase 2 against the confirmed CSV shapes in `reference/bank-csv-notes.md`
      — grilled 2026-06-28; spec in [planning/specs/phase-2-import-engine.md](planning/specs/phase-2-import-engine.md)
- [x] Run `grilling` on the Phase 2 plan before any adapter code — complete 2026-06-28
- [x] Run `domain-modeling` on Phase 2 — glossary updated, 3 ADRs written
      ([planning/decisions/2026-06-28_phase-2-import-engine.md](planning/decisions/2026-06-28_phase-2-import-engine.md))
- [x] Run `codebase-design` on Phase 2 — 5 module seams locked
      ([planning/decisions/2026-06-28_phase-2-module-seams.md](planning/decisions/2026-06-28_phase-2-module-seams.md))
- [ ] Pull **full real exports** from Bank A + Bank B (replaces template samples) — confirms
      edge cases, real amount spread for flag tuning, savings/loan shapes
- [ ] Write seed loader for `fixtures/seed/*.json` (accounts, categories, rules) for dev setup
- [ ] Promote Phase 1 schema deep-dive from PLAN.md → `planning/architecture/schema.md`
- [ ] Point `scaffold-endpoint` SKILL.md "Canonical reference" at the new `accounts` resource

## Phase 0 — Foundations & scaffolding ✅ (2026-06-27)
- [x] Repo structure: `src/backend/` (FastAPI) + `src/frontend/` (SvelteKit SPA) +
      `ops/deploy/` compose for Postgres — scaffolded 2026-06-27.
- [x] CI/CD: deferred to Phase 7 (decision record:
      [planning/decisions/2026-06-27_phase-0-auth.md](planning/decisions/2026-06-27_phase-0-auth.md)).
- [x] B-grade auth: Argon2 hashing, PostgreSQL server-side sessions (30-day sliding
      expiry), `slowapi` rate-limit on login, MFA hook seam (`mfa_secret` nullable column).
      No self-registration — users created via `cli.py create-user`.
- [x] `.gitignore` extended with Python/Node build artefacts.
- [x] `.env.example` created (placeholder values only).
- [x] Git initialised; pre-commit scan hook installed (blocks real CSVs, `.env`, and
      real-data content signatures).
- [ ] Keep real exports **outside the repo** (e.g. `~/finance-data/imports/`); the app
      reads them from there, never from the working tree.

### Phase 0 first-run checklist (before Phase 1)
- [ ] `cp .env.example .env` and set a real `POSTGRES_PASSWORD`
- [ ] `cd src/backend && uv sync` — install Python deps
- [ ] `cd src/frontend && npm install` — install Node deps
- [ ] `./ops/scripts/dev.sh` — boots Postgres, runs migrations, starts both servers
- [ ] `uv run python cli.py create-user --email you@example.com --name "You" --password X`
- [ ] Log in at http://localhost:5173, confirm session persists, log out, change password
- [ ] `uv run pytest` — all auth tests green
- [ ] 🛑 **CHECKPOINT:** confirm B-grade auth bar is met (hashing, sessions, rate-limit,
      MFA hook present). Then re-read the Phase 1 schema deep-dive — does anything about
      how auth/users turned out change the `users` table or audit relationships?
- [ ] Create test database once: `docker compose -f ops/deploy/docker-compose.yml exec db createdb -U finance finance_test`

## Tooling to revisit
- [ ] **Phase 1:** wire the official Postgres MCP server (`modelcontextprotocol/servers`)
      into `.mcp.json` — lets Claude query the DB directly to verify schema constraints
      (e.g. confirm the `transactions` dedupe-key composite UNIQUE constraint actually
      rejects a duplicate insert). Review the source before installing. Add the GitHub MCP server too if
      this repo ever goes to GitHub.

## Subfolders to create as the project evolves
Per the plan, don't build these ahead of the phase that needs them — create each when
its phase begins so the structure tracks real work, not assumptions.

- [x] **Phase 0** — `src/backend/` (`api/ services/ models/ schemas/ core/ migrations/
      tests/`) and `src/frontend/` (`src/routes/ src/lib/api/ src/lib/components/
      src/lib/stores/`). See [src/CONTEXT.md](src/CONTEXT.md) for the intended layout.
- [x] **Phase 0** — `ops/deploy/` compose files; `ops/scripts/` dev boot script.
- [x] **Phase 2** — `src/backend/adapters/` (per-bank CSV adapters: `bank_a`, `bank_b`).
- [ ] **As decisions land** — populate `planning/decisions/` (sign convention, stored
      balance, dedupe window) and `planning/specs/` (one spec per phase as you re-plan
      it at each 🛑 checkpoint).
- [ ] **As the schema firms up** — promote the Phase 1 schema deep-dive from PLAN.md
      into `planning/architecture/schema.md`.
- [ ] **Phase 3+** — `docs/guides/` import guide for family; `docs/api/` endpoint docs.
- [ ] **Phase 7** — `ops/monitoring/` config; `ops/scripts/` backup + tested-restore
      runbooks.
- [ ] **Once Phase 0/1 land reference files** — point `scaffold-endpoint` /
      `scaffold-page` at the canonical example files (see each SKILL.md "Canonical
      reference" section), replacing the "derive from PLAN.md" placeholder.

## Project setup
- [x] Scaffold workspace from the code-project blueprint (2026-06-25).
- [x] Portfolio polish: brief + success criteria, brief→solution map, removed premature
      empty dirs, Quickstart, links wired (2026-06-25).
- [ ] **Choose an open-source license** (LICENSE is currently TBA) — likely MIT or
      Apache-2.0, before sharing publicly.
