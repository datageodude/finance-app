"""GET /api/accounts — thin router; logic lives in services/accounts.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.accounts import AccountBalance, AccountSummary
from services import accounts as accounts_svc

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountSummary])
def get_accounts(
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    accounts = accounts_svc.list_accounts(db)
    return [
        AccountSummary(
            id=a.id,
            display_name=a.display_name,
            bank_code=a.bank_code,
            account_code=a.account_code,
            type=a.type,
        )
        for a in accounts
    ]


@router.get("/balances", response_model=list[AccountBalance])
def get_account_balances(
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = accounts_svc.list_accounts_with_balances(db)
    return [
        AccountBalance(
            id=a.id,
            display_name=a.display_name,
            bank_code=a.bank_code,
            type=a.type,
            current_balance=a.current_balance,
            available_balance=a.available_balance,
            last_import_at=last_import_at,
        )
        for a, last_import_at in rows
    ]
