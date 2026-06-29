# Phase 5 Flagging Engine — Decisions

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `grilling` + `domain-modeling` skills on the combined Phase 4
(Flagged transactions panel) + Phase 5 (Flagging engine) plan. Next gate before code:
`codebase-design`, then `tdd` (mandatory — Phase 5 is a dangerous phase).

Three decisions that are hard to reverse, surprising without context, and the result of
real trade-offs.

---

## 1. Flagging runs in a separate DB transaction from the import

**Decision:** The flagging engine commits in its own transaction, after the import
transaction has committed. A failure in flagging leaves the import standing. The
confirm endpoint calls `run_for_import(db, import_id)` after `run_import()` returns.

**Context:** The confirm endpoint (`POST /imports/confirm`) previously ended after
`run_import()` committed. The question was whether to extend that transaction to
include flag generation.

**Options considered:**

- **Same transaction (atomic):** If flagging fails, the import rolls back. All-or-nothing.
  Risk: a bug in the flagging engine (new, less tested code) silently blocks all imports.
- **Separate transaction (chosen):** Import commits first. A flagging failure is
  detectable (transactions with no flag rows) and recoverable via the backfill endpoint.
  The critical path (import) is not held hostage to the newer, less-tested flagging code.

**Rationale:** The import engine is Phase 2 code — fully tested, in production. The
flagging engine is new. Coupling them means a bug in the younger code can roll back the
older, proven code. "Imported but not yet flagged" is a recoverable state; "import
rolled back by a flag bug" is not.

**Consequences:**
- A `POST /flags/generate` backfill endpoint must exist to recover any import that
  completed without flags (bug during flagging, or pre-engine imports).
- The confirm endpoint returns before flags are generated; the Flagged panel may show
  zero flags briefly after a fresh import (acceptable — flags appear on refresh).
- Monitoring: a transaction with `created_at > flagging-engine-deploy-date` and no
  `flags` row is a signal worth alerting on in future.

---

## 2. UNIQUE (transaction_id, flag_type) idempotency constraint

**Decision:** Add a UNIQUE constraint on `flags (transaction_id, flag_type)` via a new
Alembic migration. The flagging engine uses `ON CONFLICT DO NOTHING` on insert.

**Context:** The flagging engine runs after every import. Without a guard, re-running
(e.g. backfill, or a confirm endpoint retried after a network failure) would insert
duplicate flag rows for the same transaction.

**Options considered:**

- **Check-before-insert:** Query for an existing flag before inserting. An extra
  round-trip per transaction, and still has a race window in concurrent imports.
- **UNIQUE constraint + ON CONFLICT DO NOTHING (chosen):** The DB enforces the
  invariant. No extra queries. Concurrent-safe. Consistent with the project's existing
  philosophy: the transactions dedupe key is also a UNIQUE constraint, not a pre-check.

**Rationale:** Let the DB enforce what a DB constraint is designed to enforce. The
project already relies on `ON CONFLICT DO NOTHING` for transaction dedupe; using the
same pattern here is consistent, simpler, and correct under concurrency.

**Consequences:**
- A new migration (`0008_flagging_idempotency` or similar) adds the constraint to
  the existing `flags` table.
- One transaction can accumulate at most one flag of each type. "A transaction flagged
  twice as `new_merchant`" is structurally impossible, not just a convention.
- Approved/dismissed flags are not recreated: if a flag exists (in any status),
  `ON CONFLICT DO NOTHING` skips the insert — the old status is preserved.

---

## 3. Per-merchant threshold overrides via merchant_threshold_overrides table

**Decision:** Add a `merchant_threshold_overrides (merchant_id, threshold, created_by,
created_at)` table. When an `over_threshold` flag is approved, the user may optionally
set a custom threshold for that merchant. The flagging engine joins this table and uses
the override threshold in place of the global `FLAG_THRESHOLD` for that merchant.

**Context:** The `over_threshold` rule fires on any debit exceeding the global threshold.
Large but expected recurring charges (e.g. a monthly mortgage repayment on a credit
account, an annual insurance premium) would re-flag every import cycle. Approving them
repeatedly trains the family to ignore the flag list — the wolf-crying failure mode.

**Options considered:**

- **Accept repeated flags:** Simple, no new table. High false-positive rate on known
  large transactions. Undermines trust in the flag list.
- **Suppress by merchant (boolean):** A `is_suppressed` column on `merchants` — never
  flag this merchant for `over_threshold`. Binary: no nuance around amount. A merchant
  might have expected $2,500 charges and also a suspicious $8,000 one.
- **Per-merchant threshold override table (chosen):** The user sets "for this merchant,
  only flag if the debit exceeds $X." Nuanced: it preserves flagging for genuinely
  unusual amounts at the same merchant, while silencing the routine ones.

**Rationale:** Amount nuance matters. A mortgage lender that normally charges $2,500
should still raise a flag if a $6,000 charge appears — a suppression boolean would miss
it. The override table allows this distinction with one extra join in the flagging query.

**Consequences:**
- New table: `merchant_threshold_overrides (merchant_id PK → merchants RESTRICT,
  threshold money_amount NOT NULL, created_by → users RESTRICT, created_at timestamptz)`.
  `merchant_id` is the PK — one override per merchant.
- The approve endpoint accepts an optional `custom_threshold: Decimal | None` body
  field. When non-null and the flag type is `over_threshold`, the service upserts a
  `merchant_threshold_overrides` row.
- The flagging engine's `over_threshold` query joins to `merchant_threshold_overrides`
  and uses `COALESCE(override.threshold, global_threshold)` per merchant.
- Override management UI (list, edit, delete overrides) deferred to Phase 6. The Phase
  5 path only creates them on approval.
