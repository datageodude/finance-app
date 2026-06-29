"""Spend vs Budget service.

One public function: get_spend_summary(db) → SpendSummary.

Query logic:
- Time window: current calendar month (server-side).
- Spend = ABS(SUM(amount WHERE amount < 0)) per category, with sub-category amounts
  rolled up to the parent via COALESCE(c.parent_id, c.id).
- Effective budget: rollforward — MAX(valid_from WHERE valid_from <= first of month).
- A category appears in rows if it has an effective budget OR net-negative actual spend.
- A category is excluded if its net sum for the month is strictly > 0 (income heuristic).
- Uncategorised (category_id IS NULL) is computed separately and never appears in rows.
- rows sorted by actual spend descending.
"""
import datetime
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import case, func, literal
from sqlalchemy.orm import Session as DBSession

from models.budget import Budget
from models.category import Category
from models.transaction import Transaction


@dataclass
class CategorySpendRow:
    category_id: int
    name: str
    actual: Decimal
    budget: Decimal | None


@dataclass
class SpendSummary:
    rows: list[CategorySpendRow]
    uncategorised_actual: Decimal
    total_actual: Decimal
    total_budget: Decimal | None
    has_transactions: bool


def get_spend_summary(db: DBSession) -> SpendSummary:
    today = datetime.date.today()
    current_month = today.replace(day=1)
    next_month = (current_month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    # --- Effective budget per top-level category (rollforward) ---
    # For each category, the effective budget is the amount from the most recent
    # budgets row where valid_from <= current_month.
    budget_subq = (
        db.query(
            Budget.category_id.label("cat_id"),
            func.max(Budget.valid_from).label("max_vf"),
        )
        .filter(Budget.valid_from <= current_month)
        .group_by(Budget.category_id)
        .subquery("latest_budget_date")
    )

    effective_budget_subq = (
        db.query(
            Budget.category_id.label("cat_id"),
            Budget.amount.label("amount"),
        )
        .join(
            budget_subq,
            (Budget.category_id == budget_subq.c.cat_id)
            & (Budget.valid_from == budget_subq.c.max_vf),
        )
        .subquery("effective_budget")
    )

    # --- Spend per top-level category for the current month ---
    # Sub-category transactions roll up to parent via COALESCE(parent_id, id).
    # Spend = ABS of negative-amount transactions only.
    # Net = SUM of all amounts (used for the income exclusion heuristic).
    spend_subq = (
        db.query(
            func.coalesce(Category.parent_id, Category.id).label("top_cat_id"),
            func.abs(
                func.sum(
                    case((Transaction.amount < 0, Transaction.amount), else_=literal(0))
                )
            ).label("actual"),
            func.sum(Transaction.amount).label("net"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.txn_date >= current_month,
            Transaction.txn_date < next_month,
            Transaction.category_id.isnot(None),
        )
        .group_by(func.coalesce(Category.parent_id, Category.id))
        .subquery("category_spend")
    )

    # --- Union: categories with a budget OR with net-negative actual spend ---
    # Pull top-level categories only (parent_id IS NULL).
    rows_q = (
        db.query(
            Category.id.label("category_id"),
            Category.name.label("name"),
            func.coalesce(spend_subq.c.actual, Decimal("0")).label("actual"),
            func.coalesce(spend_subq.c.net, Decimal("0")).label("net"),
            effective_budget_subq.c.amount.label("budget"),
        )
        .filter(Category.parent_id.is_(None))
        .outerjoin(spend_subq, Category.id == spend_subq.c.top_cat_id)
        .outerjoin(effective_budget_subq, Category.id == effective_budget_subq.c.cat_id)
        .filter(
            # Include if: has an effective budget OR has net-negative actual spend
            (effective_budget_subq.c.amount.isnot(None))
            | (spend_subq.c.net < 0)
        )
        # Exclude if: net is strictly positive (income/transfer heuristic)
        .filter(
            (spend_subq.c.net.is_(None)) | (spend_subq.c.net <= 0)
        )
        .order_by(func.coalesce(spend_subq.c.actual, Decimal("0")).desc())
        .all()
    )

    # --- Uncategorised spend (category_id IS NULL, negative amounts only) ---
    uncategorised_result = (
        db.query(
            func.abs(func.sum(Transaction.amount)).label("actual")
        )
        .filter(
            Transaction.txn_date >= current_month,
            Transaction.txn_date < next_month,
            Transaction.category_id.is_(None),
            Transaction.amount < 0,
        )
        .scalar()
    )
    uncategorised_actual = uncategorised_result or Decimal("0")

    # --- Assemble result ---
    category_rows = [
        CategorySpendRow(
            category_id=r.category_id,
            name=r.name,
            actual=r.actual or Decimal("0"),
            budget=r.budget,
        )
        for r in rows_q
    ]

    total_actual = sum((r.actual for r in category_rows), Decimal("0"))
    budgeted = [r.budget for r in category_rows if r.budget is not None]
    total_budget = sum(budgeted, Decimal("0")) if budgeted else None

    # has_transactions: any transaction at all in current month
    txn_count = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.txn_date >= current_month,
            Transaction.txn_date < next_month,
        )
        .scalar()
    )
    has_transactions = (txn_count or 0) > 0

    return SpendSummary(
        rows=category_rows,
        uncategorised_actual=uncategorised_actual,
        total_actual=total_actual,
        total_budget=total_budget,
        has_transactions=has_transactions,
    )
