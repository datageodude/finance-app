# Phase 1 Schema — Decisions

**Date:** 2026-06-28
**Status:** Accepted (supersedes the PLAN.md Phase-1 deep-dive where they differ)
**Gate:** Output of the `grilling` skill on the Phase-1 schema plan. Next gates before
code: `domain-modeling` → `codebase-design` → `tdd`.

This record captures 18 decisions taken while stress-testing the schema. Each notes the
decision and the reasoning, so a future reader (or future project reusing this DB) can
see *why*, not just *what*.

---

## Conventions (locked)

- All timestamps `timestamptz`, UTC. Surrogate `id` PK on every table except the
  `*_terms` sidecars (PK=FK) and the lookup tables (natural `code` PK).
- `DOMAIN money_amount AS numeric(14,2)` for every money column; `DOMAIN
  percentage_rate AS numeric(6,4)` for rates. Money is never float.
- Sign convention: **negative = money out** (locked, everywhere).
- Constrained-value sets are **lookup tables** with a natural `text code` PK, FK-referenced.

---

## Decisions

### 1. Dedupe key = composite UNIQUE constraint, not a hash
`UNIQUE (account_id, txn_date, amount, description_raw, balance)`. No `fingerprint` hash
column. **Why:** the constraint names the columns that define identity (transparent,
DBA-readable), compares typed values directly (no byte-stable serialization footgun),
and is exact (no collision risk). The hash's only win — a compact fixed-size index — is
irrelevant at household scale. **Consequence:** all five key columns are `NOT NULL`
(Postgres treats NULLs as distinct in a unique constraint, which would silently defeat
dedupe). Both v1 banks emit all five.

### 2. Fingerprint uses raw description + balance, not the normalised name
The dedupe key uses `description_raw` (not the normalised merchant) and includes the
running `balance`. **Why:** (a) removes the chicken-and-egg with Phase-2 normalisation —
dedupe no longer depends on normalisation having run; (b) raw text is more granular, so
two genuinely-different same-day same-amount charges are less likely to collide;
(c) including `balance` makes the legitimate "same $4.50 coffee twice today" case safe —
the running balance differs between the two, so they don't collide. **Residual risk:** a
bank that reorders same-amount same-day rows across exports could re-insert a duplicate;
both v1 banks carry a running balance, so accepted.

### 3. Balance model: immutable `opening_balance` + cached `current_balance` + reconciliation
Store both. `opening_balance` is set once at account creation and never changes;
`current_balance` is updated each import to the bank's reported latest-row balance (fast
page loads). A reconciliation check asserts `opening_balance + Σ(transactions) ==
current_balance` and warns loudly on drift. **Why:** a stored-only balance can't be
verified (no anchor); the immutable anchor gives two independent sources of truth, so a
missing import or dropped row is *detectable*. **Data-entry rule (Phase 2):**
`opening_balance` must be the balance *immediately before the earliest imported
transaction*, not the account's true historical open, or reconciliation won't close.

### 4. Loan/credit extras live in per-type sidecar tables (not nullable columns)
`loan_terms` and `credit_terms`, each `account_id` as **PK = FK** to `accounts` (the
PK=FK enforces 1:1 at the DB level). Plain `transaction`/`savings` accounts have no
sidecar row. **Why:** chosen over nullable columns on `accounts` for a reusable,
self-documenting foundation — each table means exactly one thing, no nullable-by-type
footguns, and a future account type is "add a new `*_terms` table." **Invariant the DB
doesn't enforce:** "a `loan` account has a `loan_terms` row" is enforced in the
create-account service and documented on the model (a trigger would fight the
easy-to-understand goal).

### 5. `merchants.first_seen_at` is derived, not stored
Dropped the column. "First seen" = `MIN(transactions.txn_date)` for the merchant, computed
at flag time. `created_at` remains as plain row provenance only. **Why:** correct under
any import order — a backfill of older data automatically moves "first seen" earlier, as
it should. A stored wall-clock timestamp would stamp every merchant in the first bulk
import with "today" and fire the new-merchant flag on long-established merchants when
older data is later backfilled — the cry-wolf failure Phase 5 must avoid.

### 6. `NULL` category_id = Uncategorised (no magic row)
Uncategorised is the *absence* of a category, not a seeded "Uncategorised" row. **Why:**
honest semantics, impossible to accidentally rename/delete/re-parent, and the Phase-6
success metric is a trivial `COUNT(*) WHERE category_id IS NULL`. Cost is a single
`COALESCE` in the spend rollup, isolated to the service layer.

### 7. Single self-referencing `categories` table, 2-level cap in the service
Keep `parent_id` self-reference (one table), but the service enforces: a category is
either top-level (`parent_id IS NULL`) or a sub-category whose parent is itself top-level.
**Why:** gives the simple non-recursive `GROUP BY parent` rollup the Spend page needs and
matches Bank B's Category/Subcategory shape, while lifting the cap later is a one-line
service change, not a migration. A DB CHECK can't express "my parent has no parent"
without a trigger.

### 8. Rules match against `description_raw`
`rules.match_value` is tested against `description_raw`, not the normalised merchant name.
**Why:** `description_raw` is unconditionally present at categorisation time, so
categorisation and merchant-normalisation fail *independently* rather than in series;
`contains`/`regex` are built for messy raw text. Self-improving loop still works: clearing
an Uncategorised item suggests `description_raw CONTAINS "<token>"`.

### 9. Explicit rule precedence: `priority` + first-match-wins
`rules.priority int NOT NULL DEFAULT 100`. Evaluate ascending; ties broken by `created_at`
then `id`; first match wins and stops. **Why:** the only option that is both deterministic
*and* explainable — and explainability matters because the self-improving loop keeps
adding rules. UI hides the knob (default 100) until a genuine conflict needs ordering.

### 10. Three-state flags: `open | approved | dismissed`
`flags.status` ∈ {open, approved, dismissed}; `approved_by/at` renamed to generic
`resolved_by/resolved_at`. **Why:** Phase 5 lives or dies on false-positive rate. Splitting
"reviewed, legitimate" (`approved`) from "noise, shouldn't have fired" (`dismissed`) makes
FP rate a real per-`flag_type` metric: `dismissed / (approved + dismissed)`. Two states
would throw that signal away.

### 11. Generic `audit_log` + `imports` as structured source of truth
`audit_log` is `(user_id, action, target_type, target_id, detail jsonb, created_at)` — a
generic, reusable activity stream. `imports` holds import facts (filename, counts, etc.) as
real columns; `transactions.import_id → imports`. The import's `audit_log` row is a *thin
pointer* (`action='import', target_type='import', target_id=<imports.id>`) carrying no
copied counts. **Why:** the original plan duplicated the entire import record inside the
audit JSON — two sources of truth that can drift, fatal for chain-of-custody. Every fact
now lives exactly once; the unified timeline is one query over `audit_log`. **Cost:**
`(target_type, target_id)` is polymorphic — no cross-table FK; standard activity-log
tradeoff, accepted.

### 12. Lookup tables for every constrained-value set
`banks`, `account_types`, `match_types`, `flag_statuses`, `flag_types`, `audit_actions` —
each `(code PK text, label, description?)`, FK-referenced, seeded as reference data.
**Why:** consistent with the reusable-foundation goal; a new value is an `INSERT` (no
migration); raw SQL reads `'loan'` not `47`. Native Postgres `ENUM` rejected (add-only,
painful `ALTER TYPE`, can't remove/reorder) — `flag_types` and `audit_actions` are exactly
the sets that grow. `audit_actions` as a lookup also protects the audit trail from typo'd
action strings.

### 13. `banks` lookup + composite account identity + `bank_account_name`
`accounts.bank_code → banks(code)`. `UNIQUE(bank_code, account_code)` — a code (`a1`) is
only meaningful within its bank. `bank_account_name` (nullable) stored as an import
cross-check (Bank B emits a full account name per row; the filename remains the identity).
**Why:** a real seeded `banks` table means a typo'd bank in a filename can't silently
create a phantom account; bank-scoped codes match the fixtures and the filename convention.

### 14. Money/rate precision via domains; `currency` stays a plain column
`money_amount = numeric(14,2)` and `percentage_rate = numeric(6,4)` domains, used
everywhere. `interest_rate` stores the human percentage (`5.8900`), not the fraction.
`accounts.currency text NOT NULL DEFAULT 'AUD'` stays a plain column — the *one* place a
lookup is premature, since nothing in v1 branches on currency (unlike `bank_code`, which
drives adapter choice). Promote to a `currencies` lookup when multi-currency actually lands.

### 15. Transaction mutability: bank facts immutable, interpretations editable + audited
Bank-fact columns (`account_id`, `txn_date`, `amount`, `description_raw`, `balance`) are
immutable — no update path exposed in the service (enforced in service + documented on the
model, not a DB trigger). Only `category_id` and `merchant_id` are mutable; each change
writes an `audit_log` row (`action='recategorise'`, `detail={from,to}`). `updated_at` added
for last-touched. **Why:** editing the bank facts would silently break the dedupe key and
balance reconciliation. Facts frozen, interpretations correctable with provenance.

### 16. Deletion & referential integrity
Guiding principle: **provenance and actors are never destroyed; bank facts can be
*reversed* but not silently erased; reference-data deletes degrade gracefully.**

- **Import reversal** is first-class: keeps the `imports` row (sets `reversed_at`/
  `reversed_by`), hard-deletes its `transactions` (safe — import is idempotent, so
  re-importable), cascade-removes those transactions' `flags`, writes an `audit_log`
  reversal entry. **No soft-delete tombstones** anywhere.
- `ON DELETE` map:
  | FK | Action |
  |----|--------|
  | `transactions.account_id → accounts` | RESTRICT |
  | `transactions.import_id → imports` | RESTRICT |
  | `transactions.category_id → categories` | SET NULL |
  | `transactions.merchant_id → merchants` | SET NULL |
  | `flags.transaction_id → transactions` | CASCADE |
  | `flags.related_transaction_id → transactions` | SET NULL |
  | `rules.category_id → categories` | RESTRICT |
  | `categories.parent_id → categories` | RESTRICT |
  | `*_terms.account_id → accounts` | CASCADE |
  | every `*.user_id / created_by / resolved_by → users` | RESTRICT |
  | every lookup FK (`*_type`, `*_status`, `bank_code`) | RESTRICT |
- **Archive, don't delete:** `is_active boolean DEFAULT true` on `accounts` and `users`.

### 17. Relational flag link: `flags.related_transaction_id`
Nullable `related_transaction_id → transactions (SET NULL)`. **Why:** `double_charge`
(and v1.5 `recurring_change`) are inherently about a *pair* — a single `transaction_id`
can't say which earlier charge a duplicate matches. A structured, clickable link beats
prose in `reason`, and the flagging philosophy is "each flag is explainable." Nullable
because single-transaction flags (`over_threshold`, `new_merchant`) don't use it.

### 18. *(folded into the above)* `imports.reversed_at` / `reversed_by`
Reversal state is queryable on the `imports` row itself, complementing the `audit_log`
reversal entry.

---

## Still open (data/implementation, not schema-shape)

1. **Category starter list** — draft & seed the household set (Groceries, Fuel, Utilities,
   Insurance, Mortgage, Dining, Subscriptions, Medical, …), editable in-app.
2. **Lookup seed values** — enumerate every lookup table's rows in the seed migration.
3. **Indexes** — `transactions(account_id)`, `(txn_date)`, `(category_id)`,
   `(merchant_id)`; `flags(status)`; `audit_log(target_type, target_id)`, `(created_at)`.
4. **Double-charge "N-day" window** — Phase 5 config, not Phase 1.
5. `recurring_change` flag_type seeded but unused until v1.5.

---

## Keystone test (Phase 1 "done when")

The `UNIQUE(account_id, txn_date, amount, description_raw, balance)` constraint **actually
rejects a duplicate insert** — proven with a real failing/passing assertion, not a
plausible output. Plus: migrations apply and roll back cleanly; a user, account, loan
account (+ `loan_terms`), transaction, flag, audit entry, and import batch can be inserted
and queried back with relationships intact.
