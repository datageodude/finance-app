# Personal Finance App — Build Plan

A self-hosted, family-shared personal finance app. Weekly manual CSV imports, no
automated bank feeds. Privacy-first: financial data never touches the public
internet or any third-party infrastructure.

---

## Design decisions (locked)

| Area | Decision |
|------|----------|
| **Hosting** | Home device + PostgreSQL + Tailscale. Built to "B-grade" security so internet exposure is a later switch-on, not a rebuild. |
| **Form factor** | Progressive Web App (PWA) — phone-app feel, no native/app-store work. Swipeable pages **with** persistent tab/dot navigation. |
| **Stack** | FastAPI (Python) backend holds *all* logic. Svelte frontend for presentation. Own the logic, supervise the UI. |
| **Database** | PostgreSQL. Schema migrations via Alembic. |
| **Access** | All family members have equal full-read access. Audit log records who did what (chain of custody). |
| **Import** | Drag-drop CSV. Filename convention `YYYYMMDD_bankcode_accountcode.csv`. Format-validated, idempotent (dedupe), preview-before-commit, dropdown fallback if filename unclear (doubles as training). |
| **Data model** | Generic `accounts` table with a `type` field (transaction / savings / loan / credit). Loans and cash reserves are *views* over one model, not separate systems. |
| **Banks (v1)** | Bank A + Bank B. Two CSV adapters. |
| **Categorisation** | Mix pattern: rules auto-categorise → unmatched fall to "Uncategorised" → cleared manually → clearing offers to create a rule (self-improving). |
| **Page order** | Cash reserves → Spend vs budget → Flagged → Loans → Forecast. |

### Page flow

1. **Cash reserves** — total + per bank/account *(reality first)*
2. **Spend vs budget** — whole + sub-categories
3. **Flagged transactions** — list + approve-to-clear
4. **Loans** — balances, rates, repayment progress *(a view over `type=loan`)*
5. **Forecast** — 1 / 6 / 12-month savings projection

---

## Guiding principles

- **Every phase ends with something working and testable** — never a half-built layer.
- **The dangerous logic is built and tested before family ever sees it.** Import
  integrity, dedupe, and flagging fail *silently* on financial data — go slow and
  test hard there.
- **Own the spine, supervise the surface.** Schema, import, and flagging (the parts
  that fail invisibly) are written and understood by you. Presentation layers lean
  on Claude Code.

### Critical path

```
Phase 1 (schema) → Phase 2 (import) → Phase 5 (flagging)
```

These three are where correctness *matters*. Phases 3, 4, 6 are UX and far more
forgiving — a wrong chart is obvious; a wrong dedupe rule is invisible.

### One piece of homework before serious building

Phases 1 and 2 depend on having **real CSV exports** in hand. Pull a real
transaction CSV (plus savings/loan if available) from **each account at each bank**.
The adapter work becomes concrete instead of guesswork, and it reveals whether
fields like transaction *time* or *location* even exist (they often don't).

---

## 🛑 Checkpoint protocol — READ BEFORE EACH PHASE

**This document is a living plan, not a frozen spec. Do not build ahead.**

Each phase ends with a **🛑 CHECKPOINT**. When you hit one:

1. **STOP.** Do not start the next phase automatically.
2. **Verify the "done when" bar is genuinely met** — run the `check` skill (lint +
   types + tests + build) and confirm the explicit tests named (e.g. "a duplicate
   insert is actually rejected"). A passing test, not a plausible-looking output.
3. **Surface what this phase taught you.** Real data, real CSV quirks, schema
   realities, or constraints discovered during the build almost always change the
   *next* phase. Name those changes out loud.
4. **Re-plan the next phase against what you now know** before writing any of its
   code — and **run the `grilling` skill on that re-plan** to stress-test it, then
   capture it with `to-prd` / `to-issues`. Where the next phase designs schema or a
   new resource, also run `domain-modeling` then `codebase-design` before coding. The
   later phases here are deliberately high-level — deep-dived just-in-time, not built
   from their current summaries.
5. **Resolve any relevant items** from the "Open items" list at the bottom, and
   update this file (append the deep-dive, tick off resolved items).

> **Skill gates are mandatory, not optional** (full table in `../CLAUDE.md` → Skills →
> Stage gates). Build phases use `tdd` test-first — required on the dangerous phases
> (1, 2, 5). Run each gate, surface its output, then proceed.

> Why: phases 2–8 depend on decisions that can't be made well until earlier phases
> are done (e.g. flagging scope depends on whether the real CSVs carry a time field).
> Building ahead means building on assumptions. The checkpoint is where assumptions
> get replaced with facts.

**The dangerous phases (1, 2, 5) deserve the longest pauses** — they fail *silently*
on financial data. Slow is smooth here.

---

## Phased roadmap

### Phase 0 — Foundations & scaffolding
*A running empty app you can log into. Nothing financial yet.*

- Repo structure: `backend/` (FastAPI) + `frontend/` (Svelte) + `docker-compose` for Postgres.
- Postgres in a container; FastAPI connects; Svelte talks to FastAPI. A single
  "you're logged in" page proves the whole pipe end-to-end.
- **Auth built to B-grade from day one:** per-user accounts, Argon2/bcrypt password
  hashing, real session management, login rate-limiting, MFA *hooks* stubbed (off,
  but the seams exist).
- Secrets in environment variables / `.env`, never in git (`.gitignore` from commit one).
- **Privacy boundary in place from commit one:** real data never enters the repo (only
  synthetic fixtures); install the pre-commit scan hook. Full policy:
  [../docs/data-handling.md](../docs/data-handling.md).

**Done when:** family-style login works, sessions persist, nothing hard-coded or in plaintext.

> 🛑 **CHECKPOINT — pause here.** Confirm auth genuinely meets B-grade (hashing,
> sessions, rate-limit, MFA hooks present). Before Phase 1, re-read the schema
> deep-dive with fresh eyes — does anything about how auth/users turned out change
> the `users` table or the audit relationships?

---

### Phase 1 — Data model & schema  ⭐ *most important phase*
*The database everything stands on. Expensive to change later.*

Full schema detail in the **Phase 1 deep-dive** below. In short:

- Generic `accounts` table (`type`: transaction / savings / loan / credit).
- `transactions` with a composite dedupe key (UNIQUE on account + date + amount + description + balance).
- `categories`, `rules`, `merchants` (merchant normalisation underpins both
  categorisation and new-merchant flagging).
- `audit_log` (chain of custody).
- `flags` (which transaction, which rule, approved-or-not, by whom/when).
- Alembic migrations so schema is version-controlled.

**Done when:** you can hand-insert a transaction, flag, and audit entry and query
them back. No UI — pure schema, tested in SQL.

> 🛑 **CHECKPOINT — longest pause, this is the foundation.** Verify the dedupe-key
> UNIQUE constraint *actually rejects* a duplicate insert (test it, don't assume).
> Real CSVs are already in hand — re-plan Phase 2 against the confirmed shapes in
> [reference/bank-csv-notes.md](../reference/bank-csv-notes.md). Deep-dive Phase 2
> here, in this file, *before* writing any adapter code.

---

### Phase 2 — Import engine  ⭐ *heart of the app*
*Get real Bank A + Bank B CSVs into the database safely. Backend-only first.*

> **Grilled & deep-dived 2026-06-28.** Full design in
> [specs/phase-2-import-engine.md](specs/phase-2-import-engine.md) — read it before
> building any part of the import pipeline.

- **Seed loader** (`services/seed.py`) — loads `fixtures/seed/*.json` for dev + test.
  Prerequisite for all Phase 2 tests.
- **Per-bank adapter layer** (`adapters/bank_a.py`, `adapters/bank_b.py`) with a formal
  `BankAdapter` Protocol and a dict registry (`bank_code → adapter`). Community-extensible:
  adding Bank C is one file + one registry line.
- **Filename parsing:** `YYYYMMDD_bankcode_accountcode.csv` → bank + account.
  Hard-fail on bad filename (Phase 3 adds the dropdown fallback).
- **Idempotent dedupe** via the composite `UNIQUE` constraint — `ON CONFLICT DO NOTHING`.
- **Merchant normalisation** — pure string transform; adapter supplies the hint;
  `None` hint for internal transfers (leaves `merchant_id` NULL).
- **Rule-based auto-categorisation** — first-match-wins on `description_raw`; rules loaded
  once per import; unmatched → `category_id = NULL` (Uncategorised).
- Every import is all-or-nothing (one DB transaction); writes an `audit_log` entry.
- Post-import: `current_balance` updated from `reported_balance`; reconciliation check runs.

**Done when:** dropping a real CSV from each bank lands transactions correctly —
deduped, categorised-where-possible, audited. Tested via API, no UI yet.

> 🛑 **CHECKPOINT — pause here.** Re-import the *same* file and confirm zero
> duplicates (idempotency holds on real data, not just synthetic). Check merchant
> normalisation against real messy descriptions — is it collapsing variants
> correctly, or over/under-merging? What you learn about the data here reshapes both
> the Phase 4 views and the Phase 5 flag thresholds. Re-plan Phase 3's UX against how
> the real import actually behaves.

---

### Phase 3 — Import UX (family-facing front door)
*Make Phase 2 usable by a non-techy person on a laptop.*

- **Drag-drop upload** (no file paths, no folders).
- **Preview-before-commit:** "47 found, 3 duplicates, 44 will be added — proceed?"
- **Dropdown fallback** when filename unclear ("Which account is this?") — and offer
  to rename the file correctly (the training path).
- Friendly errors, never a raw stack trace.

**Done when:** a family member, with no explanation beyond "download your CSV and
drag it here," imports successfully and understands what happened.

> 🛑 **CHECKPOINT — pause here.** Ideally watch a *real* non-techy family member try
> the import once. Where they hesitate is where the UX needs work — and it tells you
> what the viewing pages must make obvious. Re-plan Phase 4 with that in mind.

---

### Phase 4 — Viewing pages (the swipe flow)
*The actual app your family opens.*

Swipeable panels **with** persistent tab/dot navigation:

1. Cash reserves — total + per bank/account
2. Spend vs budget — whole + sub-categories
3. Flagged transactions — list + approve-to-clear
4. Loans — balances, rates, repayment progress (view over `type=loan`)
5. Forecast — 1 / 6 / 12-month savings projection

- PWA wrapper added here: home-screen icon, fullscreen, app-like feel.
- Charts kept clean and legible for a non-techy reader.

**Done when:** all five pages render real data on a phone; swipe + tabs both work;
flagged-approval persists.

> 🛑 **CHECKPOINT — pause here.** With real data on screen, the flag thresholds stop
> being guesses. Look at the actual spread of transaction amounts and merchant
> frequencies before finalising Phase 5's rules — e.g. is $100 the right threshold
> for *this* household, or noise? Re-plan Phase 5 against the data you can now see.

---

### Phase 5 — Flagging engine  ⭐
*Populate the Flagged page with real logic.*

| Rule | Scope | Notes |
|------|-------|-------|
| Over $100 (configurable) | **v1** | Simple threshold. A setting, not hard-coded. |
| Double charge | **v1** | Same amount + similar merchant within N days. |
| New merchant | **v1** | Relies on Phase-2 merchant normalisation or it false-positives everything. |
| Change in regular payment | **v1.5** | Detect recurring payments first, then flag amount shifts. Needs a few months of history. |
| ~~Unusual timing~~ | **dropped** | Confirmed: neither Bank A nor Bank B exports a time field — date only. No data to run on. See [reference/bank-csv-notes.md](../reference/bank-csv-notes.md). |
| Unusual location | **infeasible** | CSVs carry no geo/location data. The bank's own alerts remain the real fraud net. |

- Each flag is explainable ("flagged because: first time at this merchant") so
  approvals are informed.

**Done when:** real imports produce sensible flags with few false positives;
approving one clears + audits it.

> 🛑 **CHECKPOINT — pause here.** False-positive rate is the whole game: a flag list
> that cries wolf gets ignored. Tune until the flags are trustworthy *before* adding
> the self-improving categorisation loop. (Timing/location flags are formally dropped —
> the real exports carry no time or location data; see
> [reference/bank-csv-notes.md](../reference/bank-csv-notes.md).)

---

### Phase 6 — Categorisation refinement
*Close the loop on the mix pattern.*

- Clearing an "Uncategorised" item **offers to create a rule** (self-improving).
- Editable categories + rules-management UI.
- Bulk-categorise helpers for the first-month backlog.

**Done when:** uncategorised volume trends *down* week over week without manual rule-writing.

> 🛑 **CHECKPOINT — pause here.** The app is now feature-complete on your laptop.
> Before deploying, do a security re-read: any secrets crept into git? Dependencies
> current? This is the gate before real financial data lives on an always-on device.

---

### Phase 7 — Deployment & hardening (home + Tailscale)
*Off the laptop, onto the always-on home device, family connected.*

- Deploy to home device (Pi / NAS / spare machine); Postgres + app in containers.
- **Tailscale** on the device + each family member's phone/laptop → private access,
  nothing on the public internet.
- **Encrypted nightly `pg_dump`** to an off-device location.
- MFA switched on (the Phase-0 hook).
- Security pass: dependency check, no secrets in git, HTTPS end-to-end.

**Done when:** a family member taps the home-screen icon, Tailscale connects them,
the app loads — and you have a *tested* restore-from-backup.

> 🛑 **CHECKPOINT — pause here.** "Tested restore" means you actually restored from a
> backup into a clean database and it worked — not that a backup file exists. Don't
> trust an untested backup with the only copy of the family's financial history.
> Phase 8 is optional and only triggered by real need, not by default.

---

### Phase 8 — Future (not now)
- Flip to internet-accessible (Cloudflare Tunnel) *if* Tailscale ever feels like
  friction — a switch-on, not a rebuild.
- Recurring-payment flagging matures as history accumulates.
- More banks (just new adapters), spending-trend insights, exportable reports.

---

## Phase 1 deep-dive — the schema

> **Grilled & revised 2026-06-28.** This deep-dive now reflects the
> [Phase-1 schema decision record](decisions/2026-06-28_phase-1-schema.md) (18
> decisions, output of the `grilling` gate). That record is authoritative where it and
> any older prose below differ.

The foundation. Below is the conceptual model — enough to build migrations from.
Conventions: surrogate `id` PK on every table except the `*_terms` sidecars (PK=FK) and
lookup tables (natural `code` PK); timestamps are `timestamptz` (UTC); money uses a
`money_amount` domain = `numeric(14,2)`, **never** float; rates use `percentage_rate` =
`numeric(6,4)`; sign convention is **negative = money out** (locked); constrained-value
sets are **lookup tables** with a natural `text code` PK.

### Entity overview

```
users ──< audit_log              (generic activity log: actor/action/target_type/target_id)
users ──< imports ──< transactions ──< flags
accounts ──< transactions
accounts ──1:1── loan_terms / credit_terms   (per-type sidecars, PK=FK)
categories ──< transactions      (NULL category = Uncategorised)
categories ──< rules
merchants ──< transactions       (normalised payee)
lookups: banks, account_types, match_types, flag_statuses, flag_types, audit_actions
```

### `users`
Who can log in. Equal access, so no role/permission columns needed yet — but the
table exists so the audit log and approvals can attribute actions.

- `id`
- `email` (unique)
- `display_name`
- `password_hash` (Argon2/bcrypt — never plaintext)
- `mfa_secret` (nullable; the Phase-0 hook, populated when MFA switched on)
- `created_at`

### `accounts`  ⭐ generic by design
The decision that makes loans/credit/savings all *views*, not separate systems.

- `id`
- `bank_code` → `banks` (RESTRICT) — maps to a CSV adapter
- `account_code` — second half of the filename (`a1`, `a2`, …)
- `display_name` — human label ("Bank A Everyday")
- `type` → `account_types` (RESTRICT): `transaction` | `savings` | `loan` | `credit`
- `currency` — `text NOT NULL DEFAULT 'AUD'` (plain column; lookup deferred to multi-currency)
- `bank_account_name` — nullable; import cross-check (Bank B emits it per row)
- `opening_balance` — `money_amount`, **immutable** anchor (set once at creation)
- `current_balance` — `money_amount`, cached, updated each import to the bank's reported balance
- `is_active` — `boolean DEFAULT true` (archive, don't delete)
- `created_at`
- **`UNIQUE (bank_code, account_code)`** — codes are bank-scoped

Loan/credit extras live in **per-type sidecar tables**, not nullable columns:

#### `loan_terms`  (1:1, PK = FK)
- `account_id` PK → `accounts` (CASCADE) · `original_principal` (`money_amount`) ·
  `interest_rate` (`percentage_rate`) · `term_months` (int)

#### `credit_terms`  (1:1, PK = FK)
- `account_id` PK → `accounts` (CASCADE) · `credit_limit` (`money_amount`)

> Plain `transaction`/`savings` accounts have no sidecar row. "A `loan` account has a
> `loan_terms` row" is enforced in the create-account service (documented on the model).

> **Balance (resolved):** store **both** — immutable `opening_balance` + cached
> `current_balance` — and run a reconciliation check that asserts
> `opening_balance + Σ(transactions) == current_balance`, warning loudly on drift. The
> immutable anchor is what makes a missing import or dropped row *detectable*. In Phase 2,
> `opening_balance` must be the balance *immediately before the earliest imported
> transaction*, or reconciliation won't close.

### `transactions`  ⭐ the dedupe key lives here
- `id`
- `account_id` → `accounts` (RESTRICT)
- `import_id` → `imports` (RESTRICT) — the batch that created the row
- `txn_date` — `NOT NULL`, date as reported (date only; neither bank exports a time)
- `amount` — `money_amount`, `NOT NULL`; **negative = money out**
- `description_raw` — `NOT NULL`, exactly as the bank wrote it
- `balance` — `money_amount`, `NOT NULL`, the running balance on the row
- `merchant_id` → `merchants` (SET NULL, nullable until normalised)
- `category_id` → `categories` (SET NULL, nullable = "Uncategorised")
- `created_at` · `updated_at`
- **`UNIQUE (account_id, txn_date, amount, description_raw, balance)`** — the dedupe key.

> **Dedupe (resolved):** the keystone is a **composite UNIQUE constraint on the real
> columns**, not a hash column. It names what defines identity (transparent), compares
> typed values directly (no byte-stable-serialization footgun), and is exact (no collision
> risk). Uses `description_raw` (no dependency on Phase-2 normalisation) and includes
> `balance` so a legitimate same-day same-amount repeat (two identical coffees) doesn't
> collide. All five key columns are `NOT NULL` — Postgres treats NULLs as distinct in a
> unique constraint, which would silently defeat dedupe.

> **Mutability (resolved):** bank-fact columns (`account_id, txn_date, amount,
> description_raw, balance`) are **immutable** — no update path in the service. Only
> `category_id`/`merchant_id` are editable, and each change writes an `audit_log` entry.
> Editing a bank fact would silently break the dedupe key and balance reconciliation.

> **Time/location note:** confirmed — Bank A and Bank B exports are **date-only**,
> with no location data ([reference/bank-csv-notes.md](../reference/bank-csv-notes.md)).
> No `txn_time` column is carried; the Phase 5 "unusual timing" and "unusual location"
> flags are formally **dropped** for v1. If a future bank exports a time, add a nullable
> `txn_time` then.

### `merchants`  — normalisation backbone
Underpins both categorisation and new-merchant flagging.

- `id`
- `normalised_name` — e.g. "Woolworths" (unique)
- `created_at` — plain row provenance only

> **First-seen (resolved):** *no* `first_seen_at` column — derive it as
> `MIN(transactions.txn_date)` at flag time. Correct under any import order: backfilling
> older data automatically moves "first seen" earlier. A stored wall-clock stamp would
> mark every merchant in the first bulk import as "new today" and fire the new-merchant
> flag on long-established merchants when older data is later backfilled.

> The hard part isn't the table — it's the normalisation logic that maps the messy
> `description_raw` ("WOOLWORTHS 1234 SYDNEY AU") onto one `normalised_name`. That
> logic lives in Phase 2; this table is where its output lands.

### `categories`
- `id`
- `name` (unique) — editable in-app
- `parent_id` → `categories` (RESTRICT, nullable)
- `created_at`

> Single self-referencing table; the service enforces a **2-level cap** (a sub-category's
> parent must itself be top-level). Non-recursive `GROUP BY parent` rollup for the Spend
> page; lifting the cap later is a one-line service change. `NULL` `category_id` on a
> transaction *is* "Uncategorised" — no magic seeded row.

### `rules`  — the auto-categorisation engine
- `id`
- `match_type` → `match_types` (RESTRICT): `contains` | `equals` | `regex`
- `match_value` — e.g. `WOOLWORTHS`; **matched against `description_raw`**
- `category_id` → `categories` (RESTRICT)
- `priority` — `int NOT NULL DEFAULT 100`; evaluate ascending, **first-match-wins** (ties: `created_at`, `id`)
- `created_by` → `users` (RESTRICT)
- `created_at`

> Matching `description_raw` (not the normalised name) keeps categorisation and
> normalisation failing *independently*. Explicit `priority` makes precedence deterministic
> *and* explainable — needed because the self-improving loop keeps adding rules.

### `flags`  — the Flagged page
- `id`
- `transaction_id` → `transactions` (CASCADE)
- `related_transaction_id` → `transactions` (SET NULL, nullable) — the *other* charge for `double_charge`
- `flag_type` → `flag_types` (RESTRICT): `over_threshold` | `double_charge` | `new_merchant` | `recurring_change` (v1.5)
- `reason` — human-readable explanation ("first time at this merchant")
- `status` → `flag_statuses` (RESTRICT): `open` | `approved` | `dismissed`
- `resolved_by` → `users` (RESTRICT, nullable)
- `resolved_at` (nullable)
- `created_at`

> Three-state status splits "reviewed, legitimate" (`approved`) from "noise" (`dismissed`),
> making FP rate a real per-`flag_type` metric for Phase-5 tuning:
> `dismissed / (approved + dismissed)`. `related_transaction_id` makes a double-charge flag
> structurally explainable (link both sides), not prose-only.

### `imports`  — structured source of truth for a batch
Ties transactions back to the file and moment they came from. Append-only.

- `id`
- `user_id` → `users` (RESTRICT)
- `filename`
- `bank_code` → `banks` (RESTRICT) · `account_id` → `accounts` (RESTRICT)
- `rows_added` / `rows_skipped`
- `reversed_at` / `reversed_by` (nullable) — reversal keeps the row, hard-deletes its txns
- `created_at`

### `audit_log`  — chain of custody (generic, reusable)
Every mutating action. Not access control — *provenance*. Generic activity-stream shape so
it drops into future projects.

- `id`
- `user_id` → `users` (RESTRICT) — the actor
- `action` → `audit_actions` (RESTRICT) — `import` | `reverse_import` | `recategorise` | `approve_flag` | `dismiss_flag` | `create_rule` | …
- `target_type` / `target_id` — polymorphic pointer (e.g. `import`/`flag`/`rule`/`transaction`); no cross-table FK
- `detail` — `jsonb`, context only — **never copies facts** that live in `imports`/`flags`/…
- `created_at`

> The import's audit row is a *thin pointer* (`target_type='import'`, `target_id=<imports.id>`),
> not a copy of the counts — so the import record has a single source of truth (`imports`).

### Phase 1 "done when"
- Migrations apply cleanly (and roll back).
- You can hand-insert: a user, an account, a loan account (+ `loan_terms`), a transaction,
  a flag, an audit entry, an import batch — and query them back with relationships intact.
- The **composite `UNIQUE (account_id, txn_date, amount, description_raw, balance)`**
  actually rejects a duplicate insert (test it — keystone of idempotent import).
- Reconciliation: `opening_balance + Σ(transactions) == current_balance` holds, and a
  deliberately-dropped row makes it *fail* (the check has teeth).

---

## Open items to resolve as you build

1. ~~**Real CSVs** from Bank A + Bank B~~ — ✅ resolved; shapes confirmed in
   [reference/bank-csv-notes.md](../reference/bank-csv-notes.md).
2. **Category starter list** — draft a household set (Groceries, Fuel, Utilities,
   Insurance, Mortgage, Dining, Subscriptions, Medical, …), editable in-app. *(Seed data.)*
3. ~~**Sign convention**~~ — ✅ locked: **negative = money out**, everywhere.
4. ~~**Stored vs derived balance**~~ — ✅ resolved: immutable `opening_balance` + cached
   `current_balance` + reconciliation check ([decision record](decisions/2026-06-28_phase-1-schema.md) §3).
5. **Dedupe window for double-charge flag** — how many days counts as "same charge twice"?
   *(Phase 5 config, not Phase 1.)*
6. **Lookup seed values + indexes** — enumerate lookup-table rows; add indexes on
   `transactions(account_id, txn_date, category_id, merchant_id)`, `flags(status)`,
   `audit_log(target_type, target_id)`, `(created_at)` in the migration.

> The full Phase-1 schema rationale (18 grilled decisions) lives in the
> [Phase-1 schema decision record](decisions/2026-06-28_phase-1-schema.md).
