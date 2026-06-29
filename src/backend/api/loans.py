"""GET /api/loans — loan accounts with terms; logic lives in services/accounts.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.accounts import LoanDetail
from services import accounts as accounts_svc

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("", response_model=list[LoanDetail])
def get_loans(
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = accounts_svc.list_loans(db)
    return [
        LoanDetail(
            id=a.id,
            display_name=a.display_name,
            bank_code=a.bank_code,
            balance_owing=abs(a.current_balance),
            available_balance=a.available_balance,
            original_principal=lt.original_principal,
            interest_rate=lt.interest_rate,
            term_months=lt.term_months,
            start_date=lt.start_date,
            end_date=lt.end_date,
            last_import_at=last_import_at,
        )
        for a, lt, last_import_at in rows
    ]
