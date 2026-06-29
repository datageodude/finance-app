# Phase 4 Cash Reserves — Module Seams

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `codebase-design` skill on the Phase-4 Cash Reserves plan.
Next gate: build (no `tdd` mandate — Phase 4 is a UX/view phase, not a dangerous-logic
phase; targeted tests on the new service function are sufficient).

Nine seam decisions. Recorded so the build phase has unambiguous targets and future
contributors understand the shape without re-deriving it.

---

## 1. `AdapterResult.available_balance` — default None, Bank B unchanged

**Seam:** `adapters/__init__.py` — `AdapterResult` dataclass.

**Decision:** Add `available_balance: Decimal | None = None` with a Python default.
Bank B's `return AdapterResult(rows=rows, reported_balance=last_balance)` needs no
change — the default covers it. Bank A explicitly sets the field when the "Available"
preamble row is found; leaves it `None` when the row is absent.

**Why default rather than required:** All existing tests construct `AdapterResult`
without this field. A required field would break 21 adapter unit tests. The default
is the right shape: absence means "bank doesn't provide this," not "caller forgot."

---

## 2. Import engine — inline available_balance update after step 9

**Seam:** `services/import_engine.py` — `run_import()`, step 9.

**Decision:** Step 9 currently reads:
```python
account.current_balance = adapter_result.reported_balance
```
Add one line immediately after:
```python
if adapter_result.available_balance is not None:
    account.available_balance = adapter_result.available_balance
```

**Why inline, not a new service function:** `current_balance` is already updated via
direct ORM attribute assignment here, not via `accounts_svc.update_balance()`. A new
`update_available_balance()` service function would be a thin wrapper around one
attribute assignment — a shallow module. Staying inline is consistent and avoids
an unnecessary seam. An edit-UI service function can be added later if Phase 4+ needs
a manual-override endpoint for Bank B loans.

---

## 3. `services/accounts.py` — `list_accounts_with_balances` returns tuples

**Seam:** `services/accounts.py`.

**Decision:** Add:
```python
def list_accounts_with_balances(
    db: DBSession,
) -> list[tuple[Account, datetime | None]]:
```
Returns active (`is_active=True`), non-credit (`type != 'credit'`) accounts, ordered
by `type` then `display_name`, joined with a `MAX(import_batches.created_at)`
subquery to produce `last_import_at` per account.

**Why tuples, not plain `Account`:** `last_import_at` cannot come from the `Account`
model alone — it requires a join on `import_batches`. Returning `(Account, datetime | None)`
keeps all logic in one query without N+1 risk. The router maps the tuple to the
`AccountBalance` Pydantic schema.

**Why not two separate calls:** Two calls (one for accounts, one for last-import dates)
means two round-trips and assembling the join in the router — moving logic out of the
service. One join query is faster and keeps the router thin.

**Why credit excluded here, not at the router:** Credit exclusion is business logic
("credit is not cash"), not presentation logic. It belongs in the service. The router
should not need to know account-type semantics.

---

## 4. `schemas/accounts.py` — new `AccountBalance` schema alongside `AccountSummary`

**Seam:** `schemas/accounts.py`.

**Decision:** Add alongside the existing `AccountSummary`:
```python
class AccountBalance(BaseModel):
    id: uuid.UUID
    display_name: str
    bank_code: str
    type: str
    current_balance: Decimal
    available_balance: Decimal | None
    last_import_at: datetime | None
```

**Why not extend `AccountSummary`:** `AccountSummary` was built lean for the Import
dropdown — no balance data needed there. Adding balance fields to it ships unnecessary
payload to the import page on every account load. Two purpose-built schemas are
shallower than one overloaded one.

---

## 5. `api/accounts.py` — new `GET /accounts/balances`, existing route unchanged

**Seam:** `api/accounts.py`.

**Decision:** Add `GET /accounts/balances` returning `list[AccountBalance]`. The
router calls `list_accounts_with_balances(db)` and maps each tuple to `AccountBalance`.
Existing `GET /accounts` is untouched.

**Why `/accounts/balances` not `/reserves`:** The endpoint returns all active
non-credit accounts with balance data. Naming it `/reserves` would scope it to one
page; the Loans and Forecast panels will reuse the same endpoint. A generic name
keeps the interface reusable.

---

## 6. `lib/api/accounts.ts` — add `AccountBalance` + `getAccountBalances()`

**Seam:** `src/frontend/src/lib/api/accounts.ts`.

**Decision:** Add `AccountBalance` TypeScript interface and `getAccountBalances()`
calling `GET /api/accounts/balances`. Existing `AccountSummary` and `getAccounts()`
are untouched — the Import page's dropdown continues using the lean call.

---

## 7. `TabNav.svelte` — remove Import entry

**Seam:** `src/frontend/src/lib/components/TabNav.svelte`.

**Decision:** Remove `{ href: '/import', label: 'Import' }` from the tabs array.
Five tabs remain: Cash · Spend · Flagged · Loans · Forecast.

---

## 8. `+layout.svelte` — Import link in header-right

**Seam:** `src/frontend/src/routes/(app)/+layout.svelte`.

**Decision:** Add `<a href="/import">Import</a>` to the existing `header-right` div,
alongside the user name and logout button. No new component — the header already has
the right structure. Style to match the existing logout button.

---

## 9. `routes/(app)/cash/+page.svelte` — all grouping/toggle logic inline

**Seam:** `src/frontend/src/routes/(app)/cash/+page.svelte`.

**Decision:** All grouping (by type), subtotals, and toggle logic live in the page
component as Svelte derived state. No separate utility module.

- Toggle state: read from `localStorage` on mount, written on change; default `false`
  (cash-only).
- Grouping: derived from the `AccountBalance[]` response — filter and group client-side.
- Loan section: conditionally rendered only when toggle is `true` and at least one
  loan account exists in the response.
- Empty state: `last_import_at === null` → show `$0.00` and a "No imports yet" note.

**Why no utility module:** Grouping and subtotals are three lines of `Array.filter` /
`Array.reduce`. Extracting them to a module adds indirection without depth — the
deletion test fails (delete the utility, the complexity trivially returns inline).
