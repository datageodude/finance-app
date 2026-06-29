# Phase 2 — Import Engine

> **Status:** Grilled + domain-modelled + module seams locked 2026-06-28. Ready for TDD build.
> Key ADRs: [decisions/2026-06-28_phase-2-import-engine.md](../decisions/2026-06-28_phase-2-import-engine.md).
> Module seams: [decisions/2026-06-28_phase-2-module-seams.md](../decisions/2026-06-28_phase-2-module-seams.md).
> Cite this spec when building any part of the import pipeline.

---

## Problem

Family members need to import their weekly bank CSV exports into the app. The import must
be safe (no duplicates, no silent data loss), correct (right sign convention, right
account), and auditable (who imported what, when). This is the heart of the app — wrong
data here fails invisibly.

## Proposal

A backend-only import pipeline (no UI yet — Phase 3 adds drag-drop). A `POST /api/imports`
endpoint accepts a CSV file upload, parses it through a per-bank adapter, normalises
merchants, categorises via rules, dedupes via the UNIQUE constraint, and returns a
structured result. All-or-nothing: either the whole file commits or nothing does.

## Scope

**Included:**
- Seed loader (`services/seed.py`) — loads `fixtures/seed/*.json` into DB for dev + test
- Per-bank adapter layer (`adapters/bank_a.py`, `adapters/bank_b.py`) with a formal
  `BankAdapter` Protocol
- Adapter registry (dict `bank_code → BankAdapter`)
- Import engine service (`services/import_engine.py`) — orchestrates the full pipeline
- Merchant normalisation (pure string transform, no DB lookup, adapter-supplied hint)
- Rule-based categorisation (first-match-wins on `description_raw`, rules loaded once per import)
- `POST /api/imports` endpoint — `multipart/form-data`, any authenticated user
- Integration tests against the synthetic fixture corpus (TDD, mandatory)

**Excluded (later phases):**
- Drag-drop UI — Phase 3
- Dropdown fallback for bad filenames — Phase 3
- Flagging engine — Phase 5
- Category refinement UI and self-improving loop — Phase 6
- Bank B `bank_category` suggestion — ignored for v1 (carried in `ParsedRow`, not acted on)
- DB-aware fuzzy merchant matching — deferred until data shows it's needed

## Dependencies

- Phase 1 schema (migrations `0002`–`0004`) — all tables exist and tested ✅
- `fixtures/seed/` corpus — accounts, categories, rules, CSVs ✅
- `services/accounts.create_account()` — used by seed loader ✅
- `services/transactions.reconcile()` — used post-import ✅
- `services/auditing.record()` — used post-import ✅

## Locked design decisions (from grilling 2026-06-28)

### Data shapes

```python
@dataclass
class ParsedRow:
    txn_date: date
    amount: Decimal             # signed; negative = money out
    description_raw: str        # bank's raw text, whitespace-stripped; feeds dedupe key
    balance: Decimal            # running balance on this row
    normalised_name_hint: str | None  # adapter's best merchant-name guess; None = internal transfer
    bank_category: str | None   # bank-supplied category (Bank B only); import engine ignores it

@dataclass
class AdapterResult:
    rows: list[ParsedRow]
    reported_balance: Decimal   # preamble balance (Bank A) or last row balance (Bank B)

@dataclass
class ImportResult:
    import_id: int
    rows_added: int
    rows_skipped: int           # UNIQUE violations = known duplicates
    reconciliation_ok: bool
    drift: Decimal              # 0.00 if ok; gap amount if not
```

### Adapter contract (`BankAdapter` Protocol)

```python
class BankAdapter(Protocol):
    def parse(self, content: str, filename: str) -> AdapterResult: ...
```

- Every adapter strips leading/trailing whitespace from all text fields, including `description_raw`
- Every adapter supplies `normalised_name_hint` — its bank-specific best guess at the merchant name
- Return `normalised_name_hint = None` for rows that are clearly internal transfers
  (e.g. `TRANSFER TO SAVER`, `HOME LOAN REPAYMENT`, `DIRECT CREDIT PAYROLL`) — `merchant_id`
  stays NULL for those rows
- Bank A: detect header row by matching column names (not by line number); extract
  `reported_balance` from preamble; amount is already signed
- Bank B: no preamble; `reported_balance` = last row's `Balance`; convert Debit/Credit to
  signed amount; use `Original Description` (trimmed) as `description_raw`; use `Details`
  as `normalised_name_hint` starting point

### Adapter registry

```python
REGISTRY: dict[str, type[BankAdapter]] = {
    "bank_a": BankAAdapter,
    "bank_b": BankBAdapter,
}
```

Adding a new bank = one line. Formal Protocol ensures mypy catches a wrong interface at
type-check time.

### Filename convention

`YYYYMMDD_bankcode_accountcode.csv` — parsed to extract `bank_code` and `account_code`.
Hard-fail with 422 if the filename doesn't match. No dropdown fallback in Phase 2
(Phase 3 UX).

### Import pipeline (one DB transaction)

1. Parse filename → `bank_code`, `account_code` — 422 on malformed filename
2. Look up `accounts` by `(bank_code, account_code)` — 422 if not found
3. Select adapter from registry — 422 if unknown bank
4. Parse CSV content → `AdapterResult` — 422 on any parse error (with row number + reason)
5. Create `imports` row (`rows_added=0, rows_skipped=0`)
6. Load all rules into memory, sorted by `priority` ASC (ties: `created_at`, `id`)
7. For each `ParsedRow`:
   a. If `normalised_name_hint` is not None: title-case + strip → look up or create `merchants` row
   b. Apply rules against `description_raw` — first match wins → `category_id` (None = Uncategorised)
   c. `INSERT INTO transactions` — `ON CONFLICT DO NOTHING` → count added/skipped
8. Update `imports` row with final `rows_added`, `rows_skipped`
9. `account.current_balance = reported_balance` (always overwrite)
10. Run `transactions.reconcile()` → `reconciliation_ok`, `drift`
11. Write `audit_log` entry (`action='import'`, `target_type='import'`, `target_id=import.id`)
12. Commit → return `ImportResult`

Any failure at any step rolls back the entire transaction. Nothing is partially written.

### Error handling

- All failures return 422 with `{"error": "<code>", "detail": "<human message>"}`
- Error codes: `bad_filename`, `unknown_bank`, `unknown_account`, `parse_error`
- Reconciliation failure is a warning in `ImportResult`, not a hard fail — data committed,
  caller is told the books don't balance

### Merchant normalisation

- Pure string transform: `title_case(strip_whitespace(normalised_name_hint))`
- No DB lookup inside the normaliser — just `INSERT ... ON CONFLICT DO NOTHING` + fetch `id`
- Adapter is responsible for the bank-specific extraction (prefix stripping, etc.)
- Over-splitting (two "Woolworths" variants as separate merchants) is the safe failure mode

### Categorisation

- Rules loaded once per import batch (not per row) — avoids N×M DB round-trips
- Applied in `priority` ASC order against `description_raw`; first match wins
- No match → `category_id = NULL` (Uncategorised)
- `bank_category` from Bank B is carried in `ParsedRow` but not acted on

### Seed loader

- `services/seed.py` — callable from `cli.py seed-db` (dev) and pytest `conftest.py` (tests)
- Loads `fixtures/seed/accounts.json`, `categories.json`, `rules.json`
- `opening_balance` comes from `seed/accounts.json` — required at account creation, never nullable
- Dev/test only — does not run in production

### API endpoint

```
POST /api/imports
Content-Type: multipart/form-data
Body: file=<csv upload>
Auth: any authenticated session
```

Phase 3 uses this endpoint unchanged — no contract change between phases.

## Open questions (Phase 2 only)

- None — all Phase 2 decisions resolved in grilling. Phase 3 questions deferred to its checkpoint.

## Test plan (TDD order)

1. Adapter unit tests (no DB) — `BankAAdapter.parse()`, `BankBAdapter.parse()`; drives the Protocol into existence
2. Bank A full import (`20240229_bank_a_a1.csv`) — row count, sign convention, `current_balance`, audit log, `reconciliation_ok`
3. Bank B full import (`20240229_bank_b_b1.csv`) — debit/credit conversion, `description_raw` = trimmed Original Description
4. Idempotency: re-import same file → `rows_added=0`
5. Partial overlap: `20240307_bank_a_a1.csv` after Feb file → `rows_added=2`
6. Uncategorised: `ABC123 UNKNOWN PAYEE` row → `category_id = NULL`
7. Merchant reuse: same merchant across two imports → same `merchants.id`
