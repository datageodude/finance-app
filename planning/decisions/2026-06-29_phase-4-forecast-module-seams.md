# Phase 4 Forecast — Module Seams

**Date:** 2026-06-29
**Status:** Accepted
**Gate:** Output of the `codebase-design` skill on the Phase-4 Forecast panel plan.
Next gate: build (targeted tests on `get_forecast()` sufficient — Phase 4 is a UX/view
phase, not a dangerous-logic phase).

Seven seam decisions. Recorded so the build phase has unambiguous targets and future
contributors understand the shape without re-deriving it.

---

## 1. `services/forecast.py` — one deep function, all computation inside

**Seam:** new file `src/backend/services/forecast.py`.

**Decision:** Single public function `get_forecast(db: DBSession) -> ForecastResult`.
All computation lives inside: account balance sums, monthly SQL aggregation, date
window calculation, average, projection math, and warning flag. Two internal dataclasses:

```python
@dataclass
class ForecastHorizon:
    months: int
    projected_net_funds: Decimal
    delta: Decimal              # projected_net_funds − today net_funds

@dataclass
class ForecastResult:
    cash_total: Decimal         # SUM(current_balance) for transaction + savings
    loans_total: Decimal        # SUM(current_balance) for loan + credit — negative
    net_funds: Decimal          # cash_total + loans_total
    avg_monthly_change: Decimal # average of monthly net over Forecast Lookback
    months_of_data: int         # distinct months with transactions in lookback
    data_warning: bool          # True when months_of_data < 3
    horizons: list[ForecastHorizon]  # empty list when months_of_data == 0
```

**Why not add to `services/accounts.py`:** The monthly transaction aggregation is a
different query shape from anything in accounts — it spans all account types, groups
by calendar month, and computes an average. Adding it to accounts would couple
unrelated concerns and risk the balance functions used by Cash Reserves and Loans.
Locality: changes to Forecast computation stay in one file.

**Deletion test:** Remove `get_forecast()` and two SQL queries, date arithmetic, average
computation, and projection math scatter into the router. It earns its keep.

---

## 2. Date window: standard library only, no `dateutil`

**Seam:** date arithmetic inside `get_forecast()`.

**Decision:** Compute `current_month_start` and `lookback_start` using `datetime.date`
only — matching the pattern already established in `services/spend.py`:

```python
today = datetime.date.today()
current_month_start = today.replace(day=1)
m = current_month_start.month - 3
if m <= 0:
    lookback_start = current_month_start.replace(
        year=current_month_start.year - 1, month=m + 12
    )
else:
    lookback_start = current_month_start.replace(month=m)
```

**Why not `dateutil.relativedelta`:** Four lines of stdlib is clearer and adds no
dependency. The lookback is always exactly 3 months — a fixed offset, not a
calendar-complexity problem.

---

## 3. Monthly aggregation: SQL `GROUP BY DATE_TRUNC`, not Python loop

**Seam:** the aggregation query inside `get_forecast()`.

**Decision:**

```python
monthly_rows = (
    db.query(
        func.date_trunc('month', Transaction.txn_date).label('month'),
        func.sum(Transaction.amount).label('net_change'),
    )
    .join(Account, Transaction.account_id == Account.id)
    .filter(
        Account.is_active.is_(True),
        Transaction.txn_date >= lookback_start,
        Transaction.txn_date < current_month_start,
    )
    .group_by(func.date_trunc('month', Transaction.txn_date))
    .all()
)
months_of_data = len(monthly_rows)
```

Months with zero transactions don't appear — a gap month (e.g. no February imports)
correctly reduces `months_of_data` and triggers `data_warning = months_of_data < 3`.

**Why SQL aggregation, not Python loop:** Potentially thousands of transactions; GROUP
BY returns at most 3 rows regardless of history depth. O(months) data transfer vs
O(transactions). Matches the aggregation pattern already in `services/spend.py`.

---

## 4. `schemas/forecast.py` — new file

**Seam:** `src/backend/schemas/forecast.py`.

**Decision:** New file with two Pydantic schemas:

```python
class ForecastHorizonSchema(BaseModel):
    months: int
    projected_net_funds: Decimal
    delta: Decimal

class ForecastResponse(BaseModel):
    cash_total: Decimal
    loans_total: Decimal        # negative number — the signed sum
    net_funds: Decimal
    avg_monthly_change: Decimal
    months_of_data: int
    data_warning: bool
    horizons: list[ForecastHorizonSchema]  # empty list when months_of_data == 0
```

**Why a new file, not appended to `schemas/accounts.py`:** `schemas/accounts.py` serves
Cash Reserves and Loans; mixing Forecast's response shape in there couples unrelated
panels. Consistent with `schemas/spend.py`, `schemas/imports.py` — each panel slice
owns its schema file.

---

## 5. `api/forecast.py` — thin router at `/forecast`

**Seam:** `src/backend/api/forecast.py`, registered in `main.py`.

**Decision:** New router, prefix `/forecast`:

```python
router = APIRouter(prefix="/forecast", tags=["forecast"])

@router.get("", response_model=ForecastResponse)
def get_forecast_endpoint(
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = forecast_svc.get_forecast(db)
    return ForecastResponse(
        cash_total=result.cash_total,
        loans_total=result.loans_total,
        net_funds=result.net_funds,
        avg_monthly_change=result.avg_monthly_change,
        months_of_data=result.months_of_data,
        data_warning=result.data_warning,
        horizons=[
            ForecastHorizonSchema(
                months=h.months,
                projected_net_funds=h.projected_net_funds,
                delta=h.delta,
            )
            for h in result.horizons
        ],
    )
```

Register in `main.py`:
```python
from api.forecast import router as forecast_router
app.include_router(forecast_router, prefix="/api")
```

---

## 6. `lib/api/forecast.ts` — new frontend API client

**Seam:** `src/frontend/src/lib/api/forecast.ts`.

**Decision:** New file following the pattern of `loans.ts` and `spend.ts`:

```typescript
export interface ForecastHorizon {
  months: number;
  projected_net_funds: string;  // Decimal serialised as string
  delta: string;                // signed — negative when declining
}

export interface ForecastData {
  cash_total: string;
  loans_total: string;          // negative string
  net_funds: string;
  avg_monthly_change: string;
  months_of_data: number;
  data_warning: boolean;
  horizons: ForecastHorizon[];  // empty array when months_of_data === 0
}

export async function getForecast(): Promise<ForecastData> {
  const res = await fetch('/api/forecast');
  if (!res.ok) throw new Error('Failed to load forecast');
  return res.json();
}
```

---

## 7. `routes/(app)/forecast/+page.svelte` — all display logic inline

**Seam:** `src/frontend/src/routes/(app)/forecast/+page.svelte` (stub already exists).

**Decision:** All grouping, derived state, and conditional rendering inline —
following the precedent set in seam decision 9 of `2026-06-29_phase-4-module-seams.md`
(Cash Reserves page).

Key inline derivations:
- `improving = parseFloat(h.delta) >= 0` → CSS class (`positive`/`negative`) + arrow
  direction (↑/↓) per horizon card
- `horizons.length === 0` → empty state: today header still rendered, cards replaced
  with a single message ("Import at least 1 month of transactions to see your forecast")
- `data_warning` → warning banner above the three cards
- Static footnote always visible at bottom of panel

**Why no utility module:** The colour/arrow derivation is a single boolean per card.
Extracting it to a utility passes the deletion test the wrong way — delete the utility
and three ternary expressions reappear inline, which is the correct shape.

**Page structure:**
```
today header
  Cash     $XX,XXX
  Loans   −$XXX,XXX
  ─────────────────
  Funds   −$XXX,XXX

[warning banner — conditional on data_warning]

[horizon cards — 3 cards, or empty-state message]
  1 month   6 months   12 months
  $X,XXX    $X,XXX     $X,XXX
  ↑ +$XXX   ↑ +$XXX    ↑ +$XXX

[footnote: "Based on your last 3 months. Doesn't account for irregular expenses."]
```
