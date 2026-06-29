# Phase 2 Import Engine — Decisions

**Date:** 2026-06-28
**Status:** Accepted
**Gate:** Output of the `grilling` + `domain-modeling` skills on the Phase-2 import engine
plan. Full design in [../specs/phase-2-import-engine.md](../specs/phase-2-import-engine.md).
Next gates before code: `codebase-design` → `tdd`.

Three decisions from Phase 2 planning that are hard to reverse, surprising without
context, and the result of a real trade-off. Recorded so future contributors don't
re-litigate them or add "protective" logic thinking these were oversights.

---

## 1. Adapter owns merchant-name extraction

**Decision:** Each bank adapter is responsible for extracting a `normalised_name_hint`
from its own raw description format. The import engine's normaliser is a trivial
`title_case(strip_whitespace(hint))` — no bank-specific logic.

**Why:** The import pipeline is designed to be community-extensible: anyone who clones
the repo can add their own bank adapter. A central normaliser that knows how to parse
Bank A prefixes (`POS (Cr) purchase{digits}_`) and Bank B's `Details` field would force
every new adapter author to understand and modify the central normaliser. Moving the
extraction into the adapter means each bank's logic is self-contained — one file per
bank, one responsibility. The adapter author is the only person who understands their
bank's format; they should own the extraction.

**Alternatives considered:**
- Central normaliser with bank-specific branches (`if bank_code == 'bank_a': ...`) —
  rejected because it grows without bound as banks are added and couples bank-specific
  logic to the core engine.
- `details` field in `ParsedRow` as an optional hint (Bank B only) — rejected because it
  creates a conditional in the normaliser ("use `details` if present, else parse raw")
  that each new bank adapter author must understand. The `normalised_name_hint` field is
  simpler: every adapter always provides its best guess.

**Consequence:** Adding a new bank requires implementing `normalised_name_hint` extraction
in the adapter. This is documented in the `BankAdapter` Protocol and the adapter contract.
Community contributors cannot add a bank by writing only a CSV parser — they must also
implement name extraction.

---

## 2. `merchant_id = NULL` for merchant-less transactions

**Decision:** Transactions with no external merchant (account-to-account transfers, loan
repayments, payroll income) are stored with `merchant_id = NULL`. The adapter signals
this by returning `normalised_name_hint = None`. No `merchants` row is created for these
transactions.

**Why:** The new-merchant flag (Phase 5) fires when a transaction's merchant has never
been seen before. If PAYROLL or HOME LOAN REPAYMENT created a `merchants` row, the
flag would fire on the first import — a false positive that trains family members to
ignore flags. Payroll and loan repayments are regular, expected, and never suspicious.

Queries that appear to need merchant-level granularity for these transactions don't
actually require it in practice:
- **Payroll queries** run against `category_id = Income` (rule: `contains PAYROLL →
  Income`), not against a merchant.
- **Loan repayment progress** is tracked via the loan account's `current_balance` (account
  `b2`), not by tracing repayment transactions via a merchant.
- **Employer-specific income** (e.g. "income from Acme Pty Ltd") would require a
  `description_raw ILIKE` query — less clean but supported, and not a v1 requirement.

**Alternatives considered:**
- Create merchants for all rows — rejected because it causes false positives on the
  new-merchant flag for every first payroll and loan repayment. Training users to ignore
  flags defeats the flagging engine.
- Create merchants only for certain "external" merchant-less transactions (e.g. payroll,
  but not transfers) — rejected because the boundary is ambiguous and requires the adapter
  to distinguish subtypes that the rest of the system doesn't care about.

**Consequence:** Phase 5 new-merchant logic must only consider transactions where
`merchant_id IS NOT NULL`. If a future phase needs employer-level analysis, adding a
merchant for payroll rows is a schema-compatible change (the column is nullable, not
absent). Category remains the authoritative grouping mechanism for merchant-less
transactions.

---

## 3. `reported_balance` always overwrites `current_balance`

**Decision:** After every successful import, `account.current_balance` is unconditionally
set to `reported_balance` from the file — regardless of whether the file is older or
newer than previously imported data.

**Why:** The alternative — only overwrite if the new file's date range is newer than the
account's latest transaction — requires defining "newer" (latest transaction date in the
file? the filename date prefix?) and adds conditional logic that can be subtly wrong.
The simpler rule is correct for the normal case (weekly chronological imports) and fails
loudly in the edge case: importing an older file sets `current_balance` backwards, the
reconciliation check immediately reports the drift in `ImportResult`, and the user
re-imports the newer file to restore it. The drift is visible, not silent.

**Scenario:** Import December, then March (normal). Then import an old December file
again. `current_balance` drops to December's value. Reconciliation fires immediately:
`current_balance ≠ opening_balance + Σ(Dec + Jan + Feb + Mar)`. Re-import March to
restore. No data is lost; the error is surfaced.

**Alternatives considered:**
- Guard against out-of-order imports (only update if newer) — rejected because "newer"
  is ambiguous, the logic adds complexity, and the edge case is rare for a household
  doing weekly imports. The reconciliation check is the right safety net.
- Derive `current_balance` from `opening_balance + Σ(transactions)` at query time —
  rejected because it requires a full table scan per page load. The cached
  `current_balance` is the correct pattern; reconciliation is the drift detector.

**Consequence:** Out-of-order imports are not blocked — they are corrected by re-importing
the most recent file. The reconciliation warning in `ImportResult` is the signal. Do not
add "protective" date-comparison logic to the import engine — the simplicity of "always
overwrite" is intentional.
