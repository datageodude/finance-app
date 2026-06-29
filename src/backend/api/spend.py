"""GET /api/spend/summary — thin router; logic lives in services/spend.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.spend import CategorySpendRow, SpendSummary
from services import spend as spend_svc

router = APIRouter(prefix="/spend", tags=["spend"])


@router.get("/summary", response_model=SpendSummary)
def get_spend_summary(
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
