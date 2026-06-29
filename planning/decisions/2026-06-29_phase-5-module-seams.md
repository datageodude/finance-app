# Phase 4+5 Flagged Panel + Flagging Engine — Module Seams

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `codebase-design` skill on the Phase 4+5 plan.
Next gate: `tdd` (mandatory — Phase 5 is a dangerous phase). Build test-first.

Nine seam decisions. Recorded so the build phase has unambiguous targets and future
contributors understand the shape without re-deriving it.

---

## 1. Migration 0007 — UNIQUE constraint on flags + merchant_threshold_overrides

**Seam:** `migrations/versions/0007_v1_flagging.py`

**Decision:** One migration does two things:

```sql
-- 1. Idempotency constraint on flags
ALTER TABLE flags
  ADD CONSTRAINT uq_flags_txn_flag_type
  UNIQUE (transaction_id, flag_type);

-- 2. New table for per-merchant threshold overrides
CREATE TABLE merchant_threshold_overrides (
    merchant_id   integer PRIMARY KEY
                  REFERENCES merchants(id) ON DELETE RESTRICT,
    threshold     numeric(14,2) NOT NULL,
    created_by    uuid NOT NULL
                  REFERENCES users(id) ON DELETE RESTRICT,
    created_at    timestamptz NOT NULL DEFAULT now()
);
```

**Why one migration:** Both changes exist to support the flagging engine. Splitting
them into two migrations adds churn without isolation benefit — neither change is
independently useful. One migration, one rollback unit.

**Why merchant_id as PK:** One override per merchant, not one per merchant per user.
The threshold is a household-level decision; the `created_by` column records who last
set it for the audit trail, not to namespace it per user.

---

## 2. MerchantThresholdOverride model — in models/merchant.py

**Seam:** `src/backend/models/merchant.py`

**Decision:** Add `MerchantThresholdOverride` to the existing `merchant.py` file,
alongside `Merchant`. Pattern matches `models/account.py` where `LoanTerms` and
`CreditTerms` live alongside `Account`.

```python
class MerchantThresholdOverride(Base):
    __tablename__ = "merchant_threshold_overrides"

    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), primary_key=True
    )
    threshold: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

**Why merchant.py, not flag.py:** The override configures a merchant, not a flag.
It logically belongs with the thing it configures. `flag.py` contains the event (a
specific flag on a specific transaction); `merchant.py` contains standing configuration.

---

## 3. services/flagging.py — the deep module

**Seam:** `src/backend/services/flagging.py`

**Interface (5 functions, all keyword-only after `db`):**

```python
@dataclass
class FlagResult:
    flags_created: int

@dataclass
class FlagDetail:
    flag_id: int
    flag_type: str
    reason: str
    status: str
    created_at: datetime
    txn_id: uuid.UUID
    txn_date: date
    txn_amount: Decimal
    txn_description_raw: str
    account_display_name: str
    merchant_name: str | None
    related_txn_id: uuid.UUID | None
    related_txn_date: date | None
    related_txn_amount: Decimal | None

def run_for_import(db: DBSession, *, import_id: UUID) -> FlagResult: ...
def generate_for_account(db: DBSession, *, account_id: UUID) -> FlagResult: ...
def list_open_flags(db: DBSession) -> list[FlagDetail]: ...
def approve_flag(db: DBSession, *, flag_id: int, user_id: UUID, custom_threshold: Decimal | None = None) -> None: ...
def dismiss_flag(db: DBSession, *, flag_id: int, user_id: UUID) -> None: ...
```

**What the interface hides (stays inside the module):**
- All three rule implementations (`_check_over_threshold`, `_check_double_charge`,
  `_check_new_merchant`) as private functions
- `FLAG_THRESHOLD` and `DOUBLE_CHARGE_DAYS` env var reads — callers never see them
- The `merchant_threshold_overrides` join in `_check_over_threshold`
- Account type filter (`transaction`, `credit` only for `over_threshold`)
- `MIN(txn_date)` subquery for `new_merchant` first-seen derivation
- `ON CONFLICT DO NOTHING` on flag insert
- The join structure behind `list_open_flags` (flags → transactions → accounts → merchants)
- Audit log writes on approve/dismiss
- `MerchantThresholdOverride` upsert on approve when `custom_threshold` is provided

**Why `FlagDetail` dataclass in the service, not tuples:** The `list_open_flags` join
is a 4-table join (flags → transactions → accounts → merchants, plus optional
related_transaction). Returning a named dataclass with 14 fields is far clearer than a
tuple. The router maps `FlagDetail → FlagItem` directly by field name — no logic.

**Why `run_for_import` vs `generate_for_account` as separate functions:** They differ in
scope (one import's transactions vs one account's all transactions) and will have
different callers (confirm endpoint vs backfill endpoint). Making the scope explicit at
the interface avoids a conditional parameter that changes behaviour. Each is still a
thin wrapper over the private `_generate_flags(db, transactions)` core.

**Deletion test:** Delete `flagging.py` and the three rule implementations, the
override lookup, the account-type filter, and the MIN subquery all reappear in the
router. This module earns its depth.

---

## 4. schemas/flags.py — Pydantic layer

**Seam:** `src/backend/schemas/flags.py`

**Decision:** Three schemas, directly mirroring `FlagDetail`:

```python
class FlagItem(BaseModel):
    flag_id: int
    flag_type: str
    reason: str
    status: str
    created_at: datetime
    txn_id: uuid.UUID
    txn_date: date
    txn_amount: Decimal
    txn_description_raw: str
    account_display_name: str
    merchant_name: str | None
    related_txn_id: uuid.UUID | None
    related_txn_date: date | None
    related_txn_amount: Decimal | None

class ApproveRequest(BaseModel):
    custom_threshold: Decimal | None = None

class FlagActionResponse(BaseModel):
    flag_id: int
    status: str
```

**Why no separate `FlagListResponse` wrapper:** The endpoint returns `list[FlagItem]`
directly. A wrapper class with a single `items: list[FlagItem]` field adds no value
and contradicts the project's other list endpoints (e.g. `GET /accounts` returns
`list[AccountSummary]` directly).

---

## 5. api/flags.py — thin router

**Seam:** `src/backend/api/flags.py`

**Decision:** Four routes, each a 3-5 line body that delegates entirely to the
flagging service:

```
GET  /flags                → list[FlagItem]
POST /flags/{flag_id}/approve  → FlagActionResponse
POST /flags/{flag_id}/dismiss  → FlagActionResponse
POST /flags/generate       → {"flags_created": int}
```

```python
router = APIRouter(prefix="/flags", tags=["flags"])

@router.get("", response_model=list[FlagItem])
def get_open_flags(db=Depends(get_db), _user=Depends(get_current_user)):
    return [FlagItem(**vars(f)) for f in flagging.list_open_flags(db)]

@router.post("/{flag_id}/approve", response_model=FlagActionResponse)
def approve(flag_id: int, body: ApproveRequest, db=Depends(get_db), user=Depends(get_current_user)):
    flagging.approve_flag(db, flag_id=flag_id, user_id=user.id, custom_threshold=body.custom_threshold)
    db.commit()
    return FlagActionResponse(flag_id=flag_id, status="approved")

@router.post("/{flag_id}/dismiss", response_model=FlagActionResponse)
def dismiss(flag_id: int, db=Depends(get_db), user=Depends(get_current_user)):
    flagging.dismiss_flag(db, flag_id=flag_id, user_id=user.id)
    db.commit()
    return FlagActionResponse(flag_id=flag_id, status="dismissed")

@router.post("/generate", response_model=GenerateResponse)
def generate(account_id: uuid.UUID = Query(...), db=Depends(get_db), _user=Depends(get_current_user)):
    result = flagging.generate_for_account(db, account_id=account_id)
    db.commit()
    return {"flags_created": result.flags_created}
```

**Why `POST /flags/generate` not `POST /accounts/{id}/flags`:** The backfill
operation is a flagging concern, not an accounts concern. It lives in the flags
router with a `?account_id=` query param, consistent with how `/imports/history`
accepts `limit` as a query param rather than a path segment.

**Route ordering note:** FastAPI matches routes top-to-bottom. `POST /flags/generate`
must be declared *before* `POST /flags/{flag_id}/approve` and `POST /flags/{flag_id}/dismiss`
to prevent "generate" being matched as a `flag_id`. In practice these are different
HTTP methods, but explicit ordering is safer.

---

## 6. api/imports.py confirm endpoint — wiring flagging in

**Seam:** `src/backend/api/imports.py` → `confirm_csv()` function

**Decision:** Flagging runs after `db.commit()` in its own try/except. A flagging
failure does not fail the import response — it logs and continues.

```python
@router.post("/confirm", response_model=ImportResponse)
async def confirm_csv(file, account_id, db, current_user):
    content = _decode_upload(await file.read())
    try:
        result = run_import(db, content=content, filename=..., user_id=..., account_id=...)
    except ImportValidationError as exc:
        raise HTTPException(422, {"error": exc.error_code, "detail": exc.detail})
    db.commit()                          # ← import commits here

    try:                                 # ← flagging is a separate transaction
        flagging.run_for_import(db, import_id=result.import_id)
        db.commit()
    except Exception:
        db.rollback()                    # flagging failed — import still stands

    return ImportResponse(...)
```

**Why swallow flagging exceptions at the router:** A flagging bug should not surface
as a 500 to the family member who just imported their CSV. The import succeeded; the
flag gap is recoverable via `POST /flags/generate`. Logging the exception is sufficient
for diagnosis.

**Why not move flagging into `run_import`:** `run_import` is documented as "one DB
transaction." Adding a second commit inside it would break that contract and surprise
anyone reading it. The router owns commits; it is the right place to manage the
two-transaction sequence.

---

## 7. lib/api/flags.ts — TypeScript API client

**Seam:** `src/frontend/src/lib/api/flags.ts`

**Decision:** Four functions matching the four backend routes:

```typescript
export interface FlagItem {
  flagId: number;
  flagType: string;
  reason: string;
  status: string;
  createdAt: string;
  txnId: string;
  txnDate: string;
  txnAmount: number;   // Decimal serialised as number by FastAPI
  txnDescriptionRaw: string;
  accountDisplayName: string;
  merchantName: string | null;
  relatedTxnId: string | null;
  relatedTxnDate: string | null;
  relatedTxnAmount: number | null;
}

export async function getFlags(): Promise<FlagItem[]>
export async function approveFlag(flagId: number, customThreshold?: number): Promise<{flagId: number; status: string}>
export async function dismissFlag(flagId: number): Promise<{flagId: number; status: string}>
export async function generateFlags(accountId: string): Promise<{flags_created: number}>
```

**Why snake_case → camelCase mapping:** All existing API clients (`accounts.ts`,
`imports.ts`) receive snake_case JSON from FastAPI and expose camelCase to Svelte
components. Match that convention.

---

## 8. FlagCard.svelte — per-flag card

**Seam:** `src/frontend/src/lib/components/FlagCard.svelte`

**Interface:** one prop, one event:
```
prop:  flag: FlagItem
event: resolve (no payload — parent removes the card on resolution)
```

**Internal state:**
- `resolving: boolean` — disables buttons during in-flight request
- `showThresholdInput: boolean` — shown only when `flag.flagType === 'over_threshold'`
  and user clicks Approve
- `customThreshold: string` — bound to the threshold input; empty = no override

**Approve flow for over_threshold:**
1. Click Approve → `showThresholdInput = true`, render amount input + "Save & Approve" button
2. Click "Save & Approve" → call `approveFlag(flag.flagId, parsed customThreshold || undefined)`
3. On success → `dispatch('resolve')`
4. "Skip threshold" link skips the input and approves immediately with no override

**Approve flow for all other types:** single click → call `approveFlag(flag.flagId)` → dispatch `resolve`.

**Why threshold input inline, not a modal:** No modal infrastructure exists. An inline
expand-and-confirm pattern (like the ImportCard's confirming state in Phase 3) is
consistent and simpler. One component, no portal.

---

## 9. routes/(app)/flagged/+page.svelte — replace placeholder

**Seam:** `src/frontend/src/routes/(app)/flagged/+page.svelte`

**Decision:** Full replacement of the placeholder. All state is local to the page.

- `flags: FlagItem[]` — loaded via `getFlags()` on mount
- `loading: boolean`
- On `resolve` from a `FlagCard` → `flags = flags.filter(f => f.flagId !== resolved.flagId)` (remove client-side, no re-fetch)
- Empty state: displayed when `flags.length === 0` and `!loading` — "All clear — no flags to review."

**Why no re-fetch on resolve:** Re-fetching the full list on every approve/dismiss adds
a round-trip for no UX gain. The resolved card vanishes instantly; the remaining cards
are unaffected. A re-fetch would also cause a flash. Client-side removal is correct
because only the user themselves can resolve flags in this session.
