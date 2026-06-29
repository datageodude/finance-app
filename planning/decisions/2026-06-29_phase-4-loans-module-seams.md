# Phase 4 Loans Panel — Module Seams

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `codebase-design` skill on the Phase-4 Loans panel plan.
Next gate: build (no `tdd` mandate — Phase 4 is a UX/view phase; targeted tests on
the new service function are sufficient).

Seven seam decisions. Recorded so the build phase has unambiguous targets and future
contributors understand the shape without re-deriving it.

---

## 1. Migration — add `start_date` + `end_date` to `loan_terms`

**Seam:** `migrations/versions/0006_v1_loan_dates.py`

**Decision:** Add two nullable `date` columns to `loan_terms`:
```sql
ALTER TABLE loan_terms ADD COLUMN start_date date;
ALTER TABLE loan_terms ADD COLUMN end_date date;
```
Both nullable. Existing rows are unaffected. `term_months` is unchanged.

**Why `date`, not `timestamptz`:** These are calendar dates (loan start month, scheduled
payoff month) — not moments in time. `date` matches the semantic and avoids timezone
ambiguity on display.

---

## 2. `LoanTerms` model — add `start_date` + `end_date`

**Seam:** `models/account.py` — `LoanTerms` class.

**Decision:** Add:
```python
from datetime import date

start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
```

No other changes to `LoanTerms` or `Account`.

---

## 3. `services/accounts.py` — `list_loans` returns 3-tuples

**Seam:** `services/accounts.py`.

**Decision:** Add:
```python
def list_loans(
    db: DBSession,
) -> list[tuple[Account, LoanTerms, datetime | None]]:
```
Returns active (`is_active=True`) loan accounts (`type='loan'`), INNER JOINed with
`LoanTerms`, LEFT JOINed with last import timestamp, ordered by
`abs(current_balance) DESC` (largest debt first).

**Why INNER JOIN on `LoanTerms`, not LEFT JOIN:** `create_account()` enforces the
invariant that every `type='loan'` account has a `LoanTerms` row. A LEFT JOIN would
imply that a loan without terms is a valid, displayable state — it isn't. If a
loan account is missing its sidecar, it's a data integrity problem; omitting it from
the list is the correct behaviour, not displaying it with null term fields.

**Why sort in the query, not Python:** `abs(current_balance)` ordering belongs in the
DB query (`ORDER BY abs(current_balance) DESC`) rather than Python-side. The result
set is small (≤10 loans), so performance is not the reason — correctness is. Sorting
in SQL is the declared intent; a Python `.sort()` after the fact is invisible to
anyone reading the query.

**Why 3-tuples, not a named dataclass:** Consistent with the existing
`list_accounts_with_balances` pattern (2-tuples). The unpacking
`for a, lt, last_import_at in rows` is readable. Adding a new dataclass would
introduce a new type for callers to learn without adding depth — the tuple shape is
the interface here.

---

## 4. `schemas/accounts.py` — new `LoanDetail` schema with `balance_owing`

**Seam:** `schemas/accounts.py`.

**Decision:** Add alongside `AccountSummary` and `AccountBalance`:
```python
class LoanDetail(BaseModel):
    id: uuid.UUID
    display_name: str
    bank_code: str
    balance_owing: Decimal          # abs(current_balance) — always positive
    available_balance: Decimal | None
    original_principal: Decimal
    interest_rate: Decimal
    term_months: int
    start_date: date | None
    end_date: date | None
    last_import_at: datetime | None
```

**Why `balance_owing` instead of `current_balance`:** `current_balance` for loans is
stored as a negative number (money out sign convention). Exposing it raw in the
response would require every consumer to know the sign convention and apply `abs()`.
`balance_owing` is always positive, matches the domain term ("Total Owing"), and is
self-documenting. The router maps `balance_owing = abs(account.current_balance)`.

This is different from `AccountBalance` (used by Cash Reserves), which carries raw
`current_balance` because the Cash Reserves page uses signed values for its totals.
The Loans page never uses the signed value — so the schema should reflect that.

---

## 5. New `api/loans.py` — `GET /loans`, registered in `main.py`

**Seam:** `api/loans.py` (new file); `main.py`.

**Decision:** New router file:
```python
router = APIRouter(prefix="/loans", tags=["loans"])

@router.get("", response_model=list[LoanDetail])
def get_loans(db, _user):
    rows = accounts_svc.list_loans(db)
    return [
        LoanDetail(
            id=a.id,
            display_name=a.display_name,
            bank_code=a.bank_code,
            balance_owing=abs(a.current_balance),
            available_balance=a.available_balance,
            original_principal=lt.original_principal,
            interest_rate=lt.interest_rate,
            term_months=lt.term_months,
            start_date=lt.start_date,
            end_date=lt.end_date,
            last_import_at=last_import_at,
        )
        for a, lt, last_import_at in rows
    ]
```
Register in `main.py`: `app.include_router(loans_router, prefix="/api")`.

**Why a new `api/loans.py`, not adding to `api/accounts.py`:** The Loans page is a
feature, not an account operation. `api/accounts.py` handles account-level CRUD
(`GET /accounts`, `GET /accounts/balances`). A `GET /loans` route is a view over
loan-type accounts — it belongs with the feature that owns the concept, and it
establishes the pattern for future panel endpoints (`/spend`, `/flagged`).

---

## 6. New `lib/api/loans.ts` — `LoanDetail` + `getLoans()`

**Seam:** `src/frontend/src/lib/api/loans.ts` (new file).

**Decision:** New file with:
```typescript
export interface LoanDetail {
  id: string;
  display_name: string;
  bank_code: string;
  balance_owing: string;          // positive decimal string
  available_balance: string | null;
  original_principal: string;
  interest_rate: string;
  term_months: number;
  start_date: string | null;      // "YYYY-MM-DD"
  end_date: string | null;        // "YYYY-MM-DD"
  last_import_at: string | null;
}

export async function getLoans(): Promise<LoanDetail[]> { ... }
```

**Why a new `loans.ts`, not adding to `accounts.ts`:** `accounts.ts` owns
`AccountSummary` and `AccountBalance` — both used by the Import page and Cash
Reserves. `LoanDetail` is a loan-feature type; it belongs in a module that names the
feature. Keeps `accounts.ts` focused on account management concerns.

---

## 7. `routes/(app)/loans/+page.svelte` — all logic inline

**Seam:** `src/frontend/src/routes/(app)/loans/+page.svelte`.

**Decision:** All derived calculations live inline as Svelte `$derived` state. No
utility module.

- `totalOwing`: `loans.reduce((s, l) => s + parseFloat(l.balance_owing), 0)`
- `progressPct(loan)`: `(parseFloat(loan.original_principal) - parseFloat(loan.balance_owing)) / parseFloat(loan.original_principal)`
- `amountRepaid(loan)`: `parseFloat(loan.original_principal) - parseFloat(loan.balance_owing)`
- `timeRemaining(loan)`: months from today to `end_date`; shown only when `end_date`
  is not null; formatted as "X years Y months"
- Empty state: `loans.length === 0` → "No loans"
- Last updated: `last_import_at !== null` → formatted date; else "Not yet imported"

**Why inline:** `progressPct` is one expression; `amountRepaid` is one subtraction;
`timeRemaining` is a date diff. Extracting these to a utility module adds indirection
for zero depth — the deletion test fails (delete the utility, the complexity
trivially returns inline). The pattern matches `cash/+page.svelte`, which keeps
grouping and subtotal logic inline.
