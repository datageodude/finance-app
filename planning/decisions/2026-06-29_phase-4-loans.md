# Phase 4 Loans — Decisions

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `grilling` + `domain-modeling` skills on the Phase-4 Loans
panel plan. Next gate before code: `codebase-design`.

One decision that is hard to reverse, surprising without context, and the result of
a real trade-off.

---

## 1. `loan_terms` keeps `term_months` alongside `start_date` + `end_date`

**Decision:** Add `start_date` (date, nullable) and `end_date` (date, nullable) to
`loan_terms`, but retain the existing `term_months` column rather than replacing it.
All three co-exist.

**Why:** The three fields serve different purposes and can legitimately diverge:

- `term_months` — the bank-agreed original loan duration (e.g. 360 for a 30-year
  mortgage). Set at account creation; rarely changes. Always populated (required
  column). The authoritative "what the loan document says."
- `start_date` — when the loan began. User-entered; nullable until set.
- `end_date` — the scheduled payoff date. User-entered; may differ from
  `start_date + term_months` if extra repayments have brought it forward.

If a user has made significant extra repayments, `end_date` can be meaningfully
earlier than `start_date + term_months`. Replacing `term_months` with a derivation
from `end_date − start_date` would discard the original agreed term and conflate
it with the projected payoff date — two different pieces of information.

Additionally, `start_date` and `end_date` are nullable (user must enter them via
CLI). `term_months` is always available, so interest rate display and the progress
bar work even before a user has set the dates. Time-remaining display (`end_date −
today`) requires `end_date` to be set.

**Alternatives considered:**
- Replace `term_months` with `end_date − start_date` — rejected. Loses the
  authoritative original term; breaks display until both dates are set; makes
  it impossible to show "30-year loan, tracking to finish in 27 years."
- Replace `end_date` with `start_date + term_months` (computed, not stored) —
  rejected. Doesn't capture the actual projected payoff date for users who
  have paid ahead; the whole point of `end_date` is that it can diverge.

**Consequences:**
- Migration adds `start_date date` and `end_date date` to `loan_terms`, both
  nullable; existing rows are unaffected.
- `term_months` remains a required (non-nullable) column; no change.
- Display logic: show time-remaining only when `end_date` is not null; always
  show interest rate and progress bar (they don't depend on dates).
