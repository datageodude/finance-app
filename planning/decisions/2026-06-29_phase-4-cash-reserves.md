# Phase 4 Cash Reserves — Decisions

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `grilling` + `domain-modeling` skills on the Phase-4 Cash
Reserves plan. Next gate before code: `codebase-design`.

Two decisions that are hard to reverse, surprising without context, and the result of
a real trade-off.

---

## 1. available_balance is always stored positive

**Decision:** `accounts.available_balance` uses a different sign convention from
`accounts.current_balance`. `current_balance` is signed (negative = money out, matching
the transaction sign convention). `available_balance` is always stored as a positive
number — it represents accessible cash capacity, never a debt position.

**Why:** Available balance semantically means "how much you can access." It is always
a non-negative quantity. Storing it signed (where a loan's redraw would be negative,
since loans are liabilities) would contradict its meaning and require the UI to negate
it before display. The two columns serve different purposes: `current_balance` is a
running signed position; `available_balance` is an unsigned capacity. Mixing sign
conventions in the same column would silently produce wrong totals on the Cash Position
if any calling code forgot to negate.

**Alternatives considered:**
- Store `available_balance` signed (matching `current_balance`) — rejected. A loan's
  redraw would be stored as a negative number (e.g. `−$15,000`) even though it is
  money *for* the user. The UI would need to negate it, and any code forgetting to do
  so would silently subtract redraw from the Cash Position instead of adding it.

**Consequences:**
- `available_balance` must be validated as `>= 0` at the service layer on write.
- The `money_amount` domain (`numeric(14,2)`) applies; a `CHECK (available_balance >= 0)`
  constraint should be added in the migration.
- Display code reads `available_balance` as-is; no negation required.

---

## 2. available_balance sourced from bank preamble, not derived from transactions

**Decision:** `accounts.available_balance` is populated from the bank's own stated
figure in the CSV preamble (Bank A only), not computed from the transaction history.
It is updated on every import that carries the figure and left unchanged otherwise.

**Why:** Redraw available cannot be reliably derived from transaction history. Extra
repayments appear as ordinary negative-amount transactions (labelled "HOME LOAN
REPAYMENT" or similar) indistinguishable from regular repayments in the CSV. Computing
redraw would require knowing the loan's minimum repayment schedule — data the app does
not have and cannot reliably infer. The bank's own stated Available Balance is the
authoritative figure; trusting it avoids building a fragile derived calculation on
incomplete data.

**Alternatives considered:**
- Derive redraw from transaction history (sum extra repayments above scheduled minimum)
  — rejected. Requires the loan's repayment schedule, which is not in the CSV. The
  distinction between a minimum repayment and an extra repayment is not visible in the
  transaction data alone.
- Manual entry only (user types in the redraw figure) — rejected as the primary path.
  Bank A provides it automatically; manual entry would be maintenance burden and prone
  to staleness. Manual entry remains possible via a future account-edit UI for banks
  that don't provide the figure (e.g. Bank B).

**Consequences:**
- Bank A adapter must extract the "Available" preamble row and populate
  `AdapterResult.available_balance`.
- Bank B adapter sets `AdapterResult.available_balance = None`; the import engine
  leaves `accounts.available_balance` unchanged when `None` is received.
- `accounts.available_balance` reflects the bank's last-stated figure, which is as
  current as the last import — the same staleness guarantee as `current_balance`.
- If a user has a Bank B loan with redraw, a future account-edit endpoint will allow
  manual override.
