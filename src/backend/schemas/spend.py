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
