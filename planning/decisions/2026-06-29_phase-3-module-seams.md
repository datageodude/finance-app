# Phase 3 Import UX — Module Seams

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `codebase-design` skill on the Phase-3 Import UX.
ADRs: [2026-06-29_phase-3-import-ux.md](2026-06-29_phase-3-import-ux.md).
Next gate before code: build (no mandatory `tdd` — Phase 3 is a UX phase, not a
dangerous-logic phase; Playwright e2e for the import flow is the meaningful test).

---

## Module map — changes and additions

```
src/backend/
  services/
    import_engine.py   ADD preview_import() + PreviewResult; extract _parse_and_validate();
                       ADD account_id param to run_import()

  schemas/
    imports.py         ADD PreviewResponse, ImportHistoryItem
    accounts.py        NEW — AccountSummary

  api/
    imports.py         ADD POST /imports/preview; RENAME POST /imports → POST /imports/confirm;
                       ADD GET /imports/history
    accounts.py        NEW — GET /accounts (thin; calls services/accounts.list_accounts())

src/frontend/src/
  routes/(app)/
    import/+page.svelte   NEW — Import page (leftmost in swipe)

  lib/api/
    imports.ts         NEW — previewImport(), confirmImport(), getImportHistory()
    accounts.ts        NEW — getAccounts()

  lib/components/
    ImportCard.svelte  NEW — per-file state machine (skeleton → preview/error/needs_account → success)
    DropZone.svelte    NEW — drag-drop + file picker; emits files[]
    TabNav.svelte      UPDATE — add Import tab as leftmost entry
```

---

## Seam decisions

### 1. `preview_import()` is a peer function, not a mode flag

`import_engine.py` exposes two public functions with a shared private helper:

```python
# Private — not part of the module's interface
def _parse_and_validate(
    db: DBSession,
    *,
    content: str,
    filename: str,
    account_id: UUID | None,        # None = resolve from filename
) -> tuple[Account, AdapterResult]:
    """Steps 1–4 of the pipeline: filename/account resolution, adapter, CSV parse.
    Raises ImportValidationError on any failure. Does not write to DB."""

# Public — dry-run, no DB writes
def preview_import(
    db: DBSession,
    *,
    content: str,
    filename: str,
    account_id: UUID | None = None,
) -> PreviewResult:
    """Parse and validate, count duplicates via SELECT, check filename history. No writes."""

# Public — full commit (caller does db.commit())
def run_import(
    db: DBSession,
    *,
    content: str,
    filename: str,
    user_id: UUID,
    account_id: UUID | None = None,  # NEW param
) -> ImportResult:
    """Full pipeline. Unchanged except for the account_id override path."""
```

**Why not a `dry_run: bool` flag?** A boolean that changes what a function does
(write vs not write) makes the interface harder to read and test. `preview_import`
and `run_import` have meaningfully different callers, different return types, and
different DB behaviour. Two functions, shared private helper, no flag.

**`_parse_and_validate` is an internal seam** — private to `import_engine.py`,
used only by its own two public functions. Nothing outside the module ever calls it.

### 2. `account_id` override for the dropdown fallback

Both public functions accept `account_id: UUID | None`. When provided, it overrides
filename-based account resolution:

- `account_id` given → look up account by ID, get `bank_code` from the account row.
- `account_id` not given → parse filename (`YYYYMMDD_bankcode_accountcode.csv`),
  look up account by `(bank_code, account_code)`.

Either path produces the same `(Account, AdapterResult)` and the rest of the pipeline
is identical. The filename is still stored in `imports.filename` unchanged regardless.

The frontend decides which path to take — it either sends `account_id` or it doesn't.
The backend doesn't know or care why the override was used.

### 3. `PreviewResult` (dataclass) / `PreviewResponse` (Pydantic) follow existing pattern

Service layer stays Pydantic-free. The router maps dataclass → Pydantic before returning.

```python
# services/import_engine.py
@dataclass
class PreviewResult:
    account_id: UUID
    account_display_name: str
    bank_code: str
    account_code: str          # for rename hint ("YYYYMMDD_bank_a_a1.csv")
    txn_date_min: date | None
    txn_date_max: date | None
    rows_found: int
    rows_to_add: int
    rows_duplicate: int
    filename_seen_before: bool
    filename_seen_at: datetime | None   # most recent prior import of this filename

# schemas/imports.py
class PreviewResponse(BaseModel):
    account_id: UUID
    account_display_name: str
    bank_code: str
    account_code: str
    txn_date_min: date | None
    txn_date_max: date | None
    rows_found: int
    rows_to_add: int
    rows_duplicate: int
    filename_seen_before: bool
    filename_seen_at: datetime | None

class ImportHistoryItem(BaseModel):
    import_id: UUID
    filename: str
    account_display_name: str
    rows_added: int
    rows_skipped: int
    created_at: datetime
```

### 4. Duplicate detection in preview uses a single range-bounded SELECT

`preview_import` must count duplicates without writing. Rather than N individual
EXISTS checks (one per row), it loads existing dedupe keys for the account in the
CSV's date range (`txn_date BETWEEN min AND max`) in one query, then compares
in Python:

```python
existing = {
    (r.txn_date, r.amount, r.description_raw, r.balance)
    for r in db.query(Transaction.txn_date, Transaction.amount,
                      Transaction.description_raw, Transaction.balance)
              .filter_by(account_id=account.id)
              .filter(Transaction.txn_date.between(date_min, date_max))
              .all()
}
rows_duplicate = sum(
    1 for row in adapter_result.rows
    if (row.txn_date, row.amount, row.description_raw, row.balance) in existing
)
rows_to_add = rows_found - rows_duplicate
```

One query for any CSV size. Bounded to the date range so it's not a full table scan.

### 5. `GET /accounts` uses the existing `services/accounts.list_accounts()`

No new service. The function already exists and returns active accounts by default.
The new `api/accounts.py` router is a thin wrapper:

```python
@router.get("", response_model=list[AccountSummary])
def get_accounts(db = Depends(get_db), _user = Depends(get_current_user)):
    return accounts_svc.list_accounts(db)
```

`schemas/accounts.py` adds `AccountSummary(id, display_name, bank_code, account_code, type)`.
The frontend needs `bank_code` + `account_code` to construct the rename hint.

### 6. `ImportCard.svelte` owns the per-file state machine

The card is the deepest frontend component. It hides five states behind a single
`{ file }` prop:

```
loading → preview | error | needs_account
needs_account → [user picks account] → loading (re-fires preview with account_id)
preview → confirming (triggered by parent via reactive prop)
confirming → success | error
```

**Interface:**
```typescript
// Props (Svelte 5)
let {
  file,
  confirmTrigger,      // number — parent increments to trigger confirm on all ready cards
  onDismiss,           // () => void
  onReady,             // (info: { accountId: string; rowsToAdd: number }) => void
  onNotReady,          // () => void — called when card moves out of ready state (error/dismiss)
  onSuccess,           // () => void
}: { ... } = $props();
```

The parent page increments `confirmTrigger` (a shared counter) when the user clicks
"Import N files." Each card watches it with `$effect` and fires `confirmImport()`
when it sees the increment while in the `preview` state.

**Why `confirmTrigger` as a counter, not a boolean?** A boolean flag can only fire
once cleanly; a counter fires on every increment, allowing future multi-batch imports
without resetting the prop.

### 7. `DropZone.svelte` is a pure file emitter

`DropZone` handles drag-and-drop, file-picker activation, and file-type validation
(`.csv` only). It knows nothing about imports, accounts, or cards.

```typescript
// Props
let { onFiles }: { onFiles: (files: File[]) => void } = $props();
```

Rejects non-CSV drops with a brief inline message ("CSV files only"). Accepts any
number of CSV files and passes them to `onFiles`. The parent page creates one
`ImportCard` per file received.

The `<input type="file" accept=".csv" multiple>` is hidden inside `DropZone` and
activated on click — single source for both entry paths.

---

## Interface summary

| Module | Interface | Depth |
|--------|-----------|-------|
| `services/import_engine.py` | `preview_import(db, *, content, filename, account_id?)` | Deep — parse + validate + SELECT-based dedupe + filename history check |
| `services/import_engine.py` | `run_import(db, *, content, filename, user_id, account_id?)` | Very deep — unchanged pipeline + account_id override path |
| `api/imports.py` | `POST /preview`, `POST /confirm`, `GET /history` | Thin — decode, delegate, return |
| `api/accounts.py` | `GET /accounts` | Thin — auth, delegate to `list_accounts()` |
| `lib/api/imports.ts` | `previewImport()`, `confirmImport()`, `getImportHistory()` | Medium — wraps fetch, types the response |
| `lib/api/accounts.ts` | `getAccounts()` | Thin — wraps one fetch call |
| `ImportCard.svelte` | `{ file, confirmTrigger, onDismiss, onReady, onSuccess }` | Deep — entire per-file state machine hidden |
| `DropZone.svelte` | `{ onFiles }` | Medium — drag/drop + picker + validation |

---

## What the import page hides (from the user's perspective)

The `routes/(app)/import/+page.svelte` page orchestrates:

1. `DropZone` → receives `File[]` → creates one `ImportCard` per file
2. Each `ImportCard` fires `preview_import` independently; cards resolve in parallel
3. Page listens to `onReady` / `onNotReady` from each card to maintain a count
   of committable cards → drives the "Import N files" button label and enabled state
4. "Import N files" clicked → increments `confirmTrigger` → each ready card
   calls `confirm_import` independently → fires `onSuccess` when done
5. After all `onSuccess` events received → 2-second pause → drop zone resets
6. History list fetched on mount (`getImportHistory(10)`) and refreshed after
   each successful batch

The page knows nothing about CSV parsing, dedupe, or bank adapters.
