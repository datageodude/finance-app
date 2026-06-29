# Phase 2 Import Engine — Module Seams

**Date:** 2026-06-28
**Status:** Accepted
**Gate:** Output of the `codebase-design` skill on the Phase-2 import engine.
Full design: [../specs/phase-2-import-engine.md](../specs/phase-2-import-engine.md).
ADRs: [2026-06-28_phase-2-import-engine.md](2026-06-28_phase-2-import-engine.md).
Next gate before code: `tdd` (test-first, mandatory on Phase 2).

---

## Module map

```
src/backend/
  adapters/
    __init__.py      ParsedRow, AdapterResult, BankAdapter Protocol, REGISTRY, get_adapter()
    bank_a.py        BankAAdapter — implements BankAdapter
    bank_b.py        BankBAdapter — implements BankAdapter

  services/
    seed.py          load_fixtures(db) → None
    merchants.py     get_or_create(db, normalised_name) → Merchant
    import_engine.py run_import(db, *, content, filename, user_id) → ImportResult

  api/
    imports.py       POST /api/imports — thin router only

  schemas/
    imports.py       ImportResponse (Pydantic), ImportErrorResponse (Pydantic)
```

---

## Seam decisions

### 1. `adapters/__init__.py` owns `ParsedRow`, `AdapterResult`, and the `BankAdapter` Protocol

`ParsedRow` and `AdapterResult` are the adapter-layer contract — the exact interface between
bank-specific code and the import engine. They live in `adapters/` alongside the Protocol and
registry so the import engine has one import point for everything adapter-related.

They do **not** go in `schemas/` (Pydantic request/response shapes) or `core/types.py`
(monetary domain types). The seam is the adapter layer, not the API or core.

**Interface of `adapters/__init__.py`:**
```python
@dataclass
class ParsedRow:
    txn_date: date
    amount: Decimal             # signed; negative = money out
    description_raw: str        # whitespace-stripped bank text; feeds dedupe key
    balance: Decimal
    normalised_name_hint: str | None  # None = merchant-less transaction
    bank_category: str | None   # bank-supplied suggestion; import engine ignores in v1

@dataclass
class AdapterResult:
    rows: list[ParsedRow]
    reported_balance: Decimal   # bank's stated balance after last row

class BankAdapter(Protocol):
    def parse(self, content: str, filename: str) -> AdapterResult: ...

REGISTRY: dict[str, type[BankAdapter]] = {
    "bank_a": BankAAdapter,
    "bank_b": BankBAdapter,
}

def get_adapter(bank_code: str) -> BankAdapter:
    """Return an instantiated adapter for bank_code; raise ImportError on unknown bank."""
```

### 2. `services/merchants.py` — a separate module, not inline in the import engine

The import engine needs merchant lookup/create. Phase 5 (flagging engine) will also need
to query merchants for the new-merchant flag ("is this the first time we've seen this
merchant?"). That is merchant-layer logic, not flagging logic.

One caller (import engine only) would mean a hypothetical seam. Two callers (import engine
+ flagging engine) makes it real. Creating `merchants.py` now avoids duplication when
Phase 5 arrives.

**Interface:**
```python
def get_or_create(db: DBSession, normalised_name: str) -> Merchant:
    """Look up a merchant by normalised_name; create it if not found. Flushes, does not commit."""
```

Depth: hides the lookup-then-insert-if-missing logic behind a single call. Callers never
write `SELECT … INSERT … ON CONFLICT` — they call `get_or_create`.

### 3. Categorisation is an internal function of `import_engine.py`

`_categorise(description_raw: str, rules: list[Rule]) -> UUID | None` is a pure function
called in exactly one place. No other module will ever call it directly — Phase 6
re-categorisation will go through a different service path. No external seam is needed.

Keep it as a private function inside `import_engine.py`. Test it through the import engine
integration tests, not in isolation.

### 4. `run_import` receives decoded `str`, not raw `bytes`

The API router decodes the uploaded file content (UTF-8, strict) before calling `run_import`.
Encoding failures surface as 422 before the import engine is touched. The import engine and
all adapters receive and operate on `str` only.

**Adapter contract note:** content is UTF-8 decoded by the time it reaches the adapter. If a
future bank uses a different encoding (e.g. Windows-1252), the adapter or the router must
handle re-encoding before calling `parse()`. This is documented in the `BankAdapter` Protocol
docstring, not enforced by the type system.

### 5. `ImportResult` (dataclass) vs `ImportResponse` (Pydantic)

`ImportResult` is a plain dataclass returned by `services/import_engine.py`. The service
layer never imports Pydantic — that dependency belongs at the API boundary.

`ImportResponse` is a Pydantic model in `schemas/imports.py`. The router maps
`ImportResult → ImportResponse` before returning the HTTP response.

```python
# services/import_engine.py
@dataclass
class ImportResult:
    import_id: UUID
    rows_added: int
    rows_skipped: int
    reconciliation_ok: bool
    drift: Decimal

# schemas/imports.py
class ImportResponse(BaseModel):
    import_id: UUID
    rows_added: int
    rows_skipped: int
    reconciliation_ok: bool
    drift: Decimal

class ImportErrorResponse(BaseModel):
    error: str    # 'bad_filename' | 'unknown_bank' | 'unknown_account' | 'parse_error'
    detail: str
```

---

## Interface summary

| Module | Interface | Depth |
|--------|-----------|-------|
| `adapters/__init__.py` | `get_adapter(bank_code)` + data shapes | Medium — hides registry lookup |
| `adapters/bank_a.py` | `BankAAdapter.parse(content, filename)` | Deep — preamble detection, prefix stripping, signed amounts |
| `adapters/bank_b.py` | `BankBAdapter.parse(content, filename)` | Deep — debit/credit split, Details field, DD Mon YYYY dates |
| `services/merchants.py` | `get_or_create(db, normalised_name)` | Deep — lookup-then-create hidden behind one call |
| `services/seed.py` | `load_fixtures(db)` | Deep — JSON loading + account/category/rule creation |
| `services/import_engine.py` | `run_import(db, *, content, filename, user_id)` | Very deep — entire pipeline hidden behind one call |
| `api/imports.py` | `POST /api/imports` | Thin by design — decode, call service, return response |

---

## What the import engine hides

`run_import` is the deepest module. Callers (the router) see one function and one return
type. Inside, it orchestrates:

1. Filename parsing → `bank_code`, `account_code`
2. Account lookup via `(bank_code, account_code)`
3. Adapter selection via `get_adapter(bank_code)`
4. CSV parsing → `AdapterResult`
5. `imports` row creation (counts=0)
6. Rules loaded once from DB into memory
7. Per-row: merchant normalisation → `merchants.get_or_create()` → categorisation → `INSERT`
8. `imports` row updated with final counts
9. `account.current_balance` updated from `reported_balance`
10. `transactions.reconcile()` → `reconciliation_ok`, `drift`
11. `auditing.record()` → audit log entry
12. `db.commit()`

The router sees none of this.
