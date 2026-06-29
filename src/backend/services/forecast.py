"""Forecast service.

One public function: get_forecast(db) → ForecastResult.

Query logic:
- Today snapshot: SUM(current_balance) across all active accounts grouped by type.
  Cash = transaction + savings (positive); Loans = loan + credit (negative per sign
  convention). net_funds = cash_total + loans_total.
- Monthly Funds Change: SUM(transactions.amount) per complete calendar month, joined to
  active accounts only, over the last 3 complete calendar months (current partial month
  always excluded). Months with no transactions don't appear — a gap month correctly
  reduces months_of_data and triggers data_warning.
- avg_monthly_change: sum(net_change) / months_of_data, or Decimal("0") if no data.
- Horizons [1, 6, 12]: each = net_funds + avg_monthly_change * N.
- data_warning: True when months_of_data < 3.
- Empty horizons list when months_of_data == 0.
"""
import datetime
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from models.account import Account
from models.transaction import Transaction


@dataclass
class ForecastHorizon:
    months: int
    projected_net_funds: Decimal
    delta: Decimal  # projected_net_funds − today net_funds


@dataclass
class ForecastResult:
    cash_total: Decimal       # SUM(current_balance) for transaction + savings
    loans_total: Decimal      # SUM(current_balance) for loan + credit — negative
    net_funds: Decimal        # cash_total + loans_total
    avg_monthly_change: Decimal
    months_of_data: int       # distinct months with transactions in lookback window
    data_warning: bool        # True when months_of_data < 3
    horizons: list[ForecastHorizon]  # empty when months_of_data == 0


_CASH_TYPES = {"transaction", "savings"}
_LOAN_TYPES = {"loan", "credit"}
_HORIZONS = [1, 6, 12]


def get_forecast(db: DBSession) -> ForecastResult:
    today = datetime.date.today()
    current_month_start = today.replace(day=1)
    m = current_month_start.month - 3
    if m <= 0:
        lookback_start = current_month_start.replace(
            year=current_month_start.year - 1, month=m + 12
        )
    else:
        lookback_start = current_month_start.replace(month=m)

    # --- Today snapshot: balance sum by account type ---
    balance_rows = (
        db.query(Account.type, func.sum(Account.current_balance).label("total"))
        .filter(Account.is_active.is_(True))
        .group_by(Account.type)
        .all()
    )

    cash_total = Decimal("0")
    loans_total = Decimal("0")
    for row in balance_rows:
        if row.type in _CASH_TYPES:
            cash_total += row.total or Decimal("0")
        elif row.type in _LOAN_TYPES:
            loans_total += row.total or Decimal("0")

    net_funds = cash_total + loans_total

    # --- Monthly Funds Change: all active accounts, 3 complete calendar months ---
    monthly_rows = (
        db.query(
            func.date_trunc("month", Transaction.txn_date).label("month"),
            func.sum(Transaction.amount).label("net_change"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Account.is_active.is_(True),
            Transaction.txn_date >= lookback_start,
            Transaction.txn_date < current_month_start,
        )
        .group_by(func.date_trunc("month", Transaction.txn_date))
        .all()
    )

    months_of_data = len(monthly_rows)
    data_warning = months_of_data < 3

    if months_of_data == 0:
        avg_monthly_change = Decimal("0")
        horizons: list[ForecastHorizon] = []
    else:
        total_change = sum(
            (row.net_change or Decimal("0") for row in monthly_rows), Decimal("0")
        )
        avg_monthly_change = total_change / months_of_data
        horizons = [
            ForecastHorizon(
                months=n,
                projected_net_funds=net_funds + avg_monthly_change * n,
                delta=avg_monthly_change * n,
            )
            for n in _HORIZONS
        ]

    return ForecastResult(
        cash_total=cash_total,
        loans_total=loans_total,
        net_funds=net_funds,
        avg_monthly_change=avg_monthly_change,
        months_of_data=months_of_data,
        data_warning=data_warning,
        horizons=horizons,
    )
