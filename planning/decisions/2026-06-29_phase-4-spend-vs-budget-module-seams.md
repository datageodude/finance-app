# Phase 4 Spend vs Budget — Module Seams

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `codebase-design` skill on the Phase-4 Spend vs Budget panel.
Next gate: build (`tdd` not mandated here — Phase 4 is a UX/view phase; targeted service
tests are sufficient).

Eight seam decisions. Recorded so the build phase has unambiguous targets and future
contributors understand the shape without re-deriving it.

---

## 1. Migration `0007_v1_budgets` — schema only, no seed data

**Seam:** `src/backend/migrations/versions/0007_v1_budgets.py`

**Decision:** The migration creates the `budgets` table and nothing else:

```sql
CREATE TABLE budgets (
    id          SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    valid_from  DATE    NOT NULL,
    amount      NUMERIC(14,2) NOT NULL,
    created_by  UUID    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (category_id, valid_from),
    CHECK (EXTRACT(day FROM valid_from) = 1)
);
CREATE INDEX ix_budgets_category_valid_from ON budgets (category_id, valid_from);
```

The index on `(category_id, valid_from)` serves the rollforward query directly:
`WHERE category_id = ? AND valid_from <= ?` with `ORDER BY valid_from DESC LIMIT 1`.

**Why schema only, not seed data:** Migrations are schema changes; seed data is a
dev/test concern owned by `services/seed.py`. Mixing them means the migration silently
fails on a fresh database (no users exist yet — the `created_by` FK would have nothing
to reference). The seed loader handles data population once the schema exists.

---

## 2. `src/backend/models/budget.py` — new ORM model

**Seam:** `src/backend/models/budget.py`

**Decision:**

```python
import datetime
import uuid
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base
from core.types import MoneyAmount

class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MoneyAmount, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("category_id", "valid_from", name="uq_budgets_category_month"),
        CheckConstraint(
            "EXTRACT(day FROM valid_from) = 1",
            name="ck_budgets_valid_from_first_of_month",
        ),
    )
```

`id` is `SERIAL` (int autoincrement), consistent with `categories.id`. No ORM
relationship to `Category` — the service queries by join, not by lazy-loading through
the model. No `relationship()` means no accidental N+1.

The model must be registered in `src/backend/models/__init__.py` so Alembic sees it.

---

## 3. `services/seed.py` — `_load_categories` updated to insert budget rows

**Seam:** `services/seed.py` — `_load_categories(db, *, user_id)`.

**Decision:** `_load_categories` gains a `user_id` parameter and inserts a `Budget` row
for each category that has a non-null `budget` in `categories.json`:

```python
def _load_categories(db: DBSession, *, user_id: UUID) -> None:
    import datetime
    from models.budget import Budget

    data = json.loads((_SEED_DIR / "categories.json").read_text())
    today = datetime.date.today()
    valid_from = today.replace(day=1)   # first of current month

    for entry in data:
        cat = Category(name=entry["name"])
        db.add(cat)
        db.flush()   # get cat.id before Budget insert
        if entry.get("budget") is not None:
            db.add(Budget(
                category_id=cat.id,
                valid_from=valid_from,
                amount=Decimal(entry["budget"]),
                created_by=user_id,
            ))
    db.flush()
```

The caller `load_fixtures(db, *, user_id)` already has `user_id` and passes it through
to `_load_categories`. Signature change is additive — `_load_categories` was private
(`_` prefix), so no external callers to update.

**Why first-of-current-month for the seed `valid_from`:** The Spend page queries
`MAX(valid_from) WHERE valid_from ≤ current month`. Using today's first-of-month means
the seed budget is immediately visible on the Spend page the moment seeds load, with
no further configuration needed. Future months inherit via rollforward.

---

## 4. `services/spend.py` — one function, two inclusion paths, one result object

**Seam:** `services/spend.py` — `get_spend_summary(db)` → `SpendSummary`.

**Decision:** One function, one return type. No sub-functions exposed at the module
interface.

```python
@dataclass
class CategorySpendRow:
    category_id: int
    name: str
    actual: Decimal      # always positive (abs of negative txns)
    budget: Decimal | None  # None = no effective budget for this month

@dataclass
class SpendSummary:
    rows: list[CategorySpendRow]   # expense rows, sorted by actual desc
    uncategorised_actual: Decimal  # 0 if no NULL-category txns this month
    total_actual: Decimal          # sum of rows[*].actual
    total_budget: Decimal | None   # None if no rows have a budget
    has_transactions: bool         # False → no-data state note shown
```

**Query logic (two inclusion paths):**

A category appears in `rows` if either:
1. It has an effective budget for the current month (rollforward: `MAX(valid_from ≤ first_of_month)`), OR
2. It has net-negative transactions in the current month.

A category is excluded if its net sum for the month is strictly > 0.

Only top-level categories appear (`parent_id IS NULL`). Sub-category transactions
(where `parent_id IS NOT NULL`) are grouped under their parent via:
`COALESCE(c.parent_id, c.id)` as the grouping key.

Uncategorised transactions (`category_id IS NULL`) are summed separately; never appear
in `rows`. They are always `ABS(sum of negative-amount txns with NULL category)`.

The rollforward uses a lateral subquery or correlated subquery per category:
```sql
SELECT MAX(b.valid_from)
FROM budgets b
WHERE b.category_id = effective_cat_id
  AND b.valid_from <= :current_month
```

**Why one function:** The page needs all three elements (rows, uncategorised, totals) in
one response. Breaking into `get_category_rows()` + `get_uncategorised()` + `get_totals()`
would require three DB round-trips for data that comes from the same table scan. One
function, one query plan, one call site to test.

**Deletion test:** Delete `get_spend_summary`. The rollforward join, the two-path
inclusion logic, the net-positive exclusion, and the sub-category rollup all reappear
in the caller. The module is earning its keep.

---

## 5. `schemas/spend.py` — new file, mirrors service dataclasses

**Seam:** `src/backend/schemas/spend.py`

**Decision:**

```python
from decimal import Decimal
from pydantic import BaseModel

class CategorySpendRow(BaseModel):
    category_id: int
    name: str
    actual: Decimal
    budget: Decimal | None

class SpendSummary(BaseModel):
    rows: list[CategorySpendRow]
    uncategorised_actual: Decimal
    total_actual: Decimal
    total_budget: Decimal | None
    has_transactions: bool
```

Mirrors the service dataclass field-for-field. The router constructs the Pydantic
`SpendSummary` explicitly from the service dataclass, following the existing pattern
in `api/accounts.py`.

---

## 6. `api/spend.py` — new router, one endpoint, thin mapping

**Seam:** `src/backend/api/spend.py` + `main.py`

**Decision:**

```python
router = APIRouter(prefix="/spend", tags=["spend"])

@router.get("/summary", response_model=SpendSummary)
def get_spend_summary_endpoint(
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = spend_svc.get_spend_summary(db)
    return SpendSummary(
        rows=[
            CategorySpendRow(
                category_id=r.category_id,
                name=r.name,
                actual=r.actual,
                budget=r.budget,
            )
            for r in result.rows
        ],
        uncategorised_actual=result.uncategorised_actual,
        total_actual=result.total_actual,
        total_budget=result.total_budget,
        has_transactions=result.has_transactions,
    )
```

Registered in `main.py` as `app.include_router(spend_router, prefix="/api")`.

No query parameters — current month is always server-side. A `?month=YYYY-MM` parameter
can be added in Phase 6 when a month picker is introduced.

---

## 7. `lib/api/spend.ts` — new file, typed client

**Seam:** `src/frontend/src/lib/api/spend.ts`

**Decision:**

```typescript
export interface CategorySpendRow {
  category_id: number;
  name: string;
  actual: string;        // Decimal serialised as string by FastAPI
  budget: string | null;
}

export interface SpendSummary {
  rows: CategorySpendRow[];
  uncategorised_actual: string;
  total_actual: string;
  total_budget: string | null;
  has_transactions: boolean;
}

export async function getSpendSummary(): Promise<SpendSummary> {
  const res = await fetch('/api/spend/summary');
  if (!res.ok) throw new Error('Failed to load spend summary');
  return res.json();
}
```

Decimal values arrive as strings (FastAPI serialises `Decimal` to string). The page
component converts with `parseFloat()` for arithmetic and `Intl.NumberFormat` for
display — same pattern as `cash/+page.svelte`.

---

## 8. `routes/(app)/spend/+page.svelte` — all logic inline, no sub-component

**Seam:** `src/frontend/src/routes/(app)/spend/+page.svelte`

**Decision:** All state, derived values, and display logic inline. No utility module.
Following the Cash Reserves precedent exactly.

- `onMount` → `getSpendSummary()` → `summary` state.
- `loading`, `error`, `summary` reactive state.
- Grand total derived inline: `parseFloat(summary.total_actual)` vs
  `parseFloat(summary.total_budget ?? '0')`.
- Over-budget colour: `parseFloat(row.actual) > parseFloat(row.budget ?? 'Infinity')`
  → red (`#dc2626`), else normal (`#111827`).
- No-data note: shown when `!summary.has_transactions`.
- Uncategorised row rendered separately after the main list (pinned last).
- `fmt(value: number)` inline formatter — same `Intl.NumberFormat('en-AU', {style:'currency', currency:'AUD'})` as Cash.

**Why no sub-component:** The spend rows are simple two-column lines (name | actual /
budget). Extracting a `SpendRow` component adds a component boundary, props interface,
and a file — more interface than the three lines of markup it wraps. The deletion test
fails: delete the hypothetical component and the complexity trivially returns inline.
