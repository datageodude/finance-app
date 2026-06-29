# Phase 4 Forecast — Decisions

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `grilling` + `domain-modeling` skills on the Phase-4 Forecast
panel plan. Next gate before code: `codebase-design`.

---

## 1. Forecast metric is Funds (all active accounts), not Cash Position

**Decision:** The Forecast panel projects **Funds** — the signed sum of all active
account `current_balance` values including loans and credit cards — not Cash Position
(transaction + savings only, as used on the Cash Reserves page).

**Why:** A cash-only projection systematically misrepresents the household's trajectory.
A mortgage repayment is a cash debit (-$2,000 from the transaction account) and a
liability reduction (+$2,000 off the loan balance). Cash Position would record it as a
$2,000 hit to savings rate; Funds records the net correctly as $0 equity change (only
the interest component is a true cost). Projecting cash-only would show savings rate as
worse than reality whenever significant loan repayments occur — the most common household
scenario. The Funds basis gives an honest equity-view projection using only data the app
actually holds, without needing property or investment valuations.

**Alternatives considered:**
- **Cash Position only (transaction + savings accounts)** — rejected. Loan repayments
  register as expenses, understating the savings rate. The projection would worsen as
  repayments grow — the opposite of the financial reality.
- **Net worth (including property and investment assets)** — rejected. The app tracks
  bank accounts only; property values and superannuation are outside the data model.
  Calling it "net worth" would overstate what the app knows and imply completeness it
  cannot deliver.
- **Separate cash and loan projections (two numbers)** — rejected for v1. Adds two
  extra horizon cards (6 numbers on screen instead of 3) without adding actionable
  insight. The net Funds figure with a Cash/Loans breakdown in the "today" header
  provides context without multiplying the projection cards.

**Consequences:**
- The Forecast endpoint must query all active accounts (`is_active = true`), not just
  type `transaction` and `savings`.
- Inactive accounts (closed accounts, `is_active = false`) are excluded — their balance
  is a residual artefact, not a live position.
- The monthly change average must also span all active accounts, for the same reason:
  a loan-only average would miss cash flow; a cash-only average would double-count
  repayments as costs.
- `available_balance` (redraw) is **not** used in the Forecast — the projection uses
  `current_balance` only. Redraw is already embedded in the loan's `current_balance`
  (extra repayments reduce the outstanding balance). Reclassifying redraw as cash for
  the Forecast would require amortisation schedule data the app does not hold.
- The "today" header displays: Cash (sum of transaction + savings `current_balance`) /
  Loans (sum of loan + credit `current_balance`, displayed as negative) / Net (the
  Funds total). This breakdown makes the signed arithmetic visible and auditable.

---

## 2. Forecast lookback excludes the current (partial) calendar month

**Decision:** The average Monthly Funds Change is computed from the 3 most recent
**complete** calendar months. The current month is always excluded from the lookback,
even on the last day of the month.

**Why:** A partial month's transaction total is smaller in absolute terms than a full
month and distorts the average in proportion to how early in the month it is. A user
who imports on the 5th of July would have only 5 days of July transactions; including
July would drag the average down and project a falsely pessimistic trajectory. Excluding
the current month always produces a stable, auditable average — one the user can verify
against three months they can name and remember.

**Alternatives considered:**
- **Include current month, pro-rate to full month** — rejected. Pro-rating multiplies
  partial data by a ratio the user cannot easily verify ("why does it say $3,400 for
  June when I've only spent $2,100 so far?"). It also amplifies noise early in the
  month when the signal is weakest.
- **Include current month as-is** — rejected. Systematically understates the average
  for any month with significant late-month expenses (rent, mortgage, pay cycle end).

**Consequences:**
- A brand-new install with imports only in the current calendar month has zero complete
  months and displays the "today" header with an empty-state message in place of the
  three horizon cards.
- When fewer than 3 complete months exist, a warning banner is shown: the projection is
  available but flagged as less reliable.
- The service computes the lookback boundary as: first day of the current month, then
  takes the 3 prior months.
