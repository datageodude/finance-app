from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from models.account import Account, CreditTerms, LoanTerms
from models.import_batch import ImportBatch


class MissingSidecarError(ValueError):
    """Raised when a loan or credit account is created without its required terms."""


def create_account(
    db: DBSession,
    *,
    bank_code: str,
    account_code: str,
    display_name: str,
    type: str,
    opening_balance: Decimal,
    current_balance: Decimal,
    created_by_user_id: UUID,
    currency: str = "AUD",
    bank_account_name: Optional[str] = None,
    loan_terms: Optional[dict] = None,
    credit_terms: Optional[dict] = None,
) -> Account:
    """Create an account and its sidecar (if required).

    Invariant: type='loan' requires loan_terms; type='credit' requires credit_terms.
    Enforced here because the DB cannot express "sidecar must exist" without a trigger.
    """
    if type == "loan" and loan_terms is None:
        raise MissingSidecarError("A loan account requires loan_terms")
    if type == "credit" and credit_terms is None:
        raise MissingSidecarError("A credit account requires credit_terms")

    account = Account(
        bank_code=bank_code,
        account_code=account_code,
        display_name=display_name,
        type=type,
        opening_balance=opening_balance,
        current_balance=current_balance,
        currency=currency,
        bank_account_name=bank_account_name,
    )
    db.add(account)
    db.flush()  # get account.id before inserting sidecars

    if type == "loan" and loan_terms is not None:
        db.add(LoanTerms(account_id=account.id, **loan_terms))

    if type == "credit" and credit_terms is not None:
        db.add(CreditTerms(account_id=account.id, **credit_terms))

    db.flush()
    return account


def get_account(db: DBSession, account_id: UUID) -> Optional[Account]:
    return db.get(Account, account_id)


def list_accounts(db: DBSession, *, include_inactive: bool = False) -> list[Account]:
    q = db.query(Account)
    if not include_inactive:
        q = q.filter(Account.is_active.is_(True))
    return q.all()


def archive_account(db: DBSession, account_id: UUID, archived_by_user_id: UUID) -> Account:
    account = db.get(Account, account_id)
    account.is_active = False
    db.flush()
    return account


def update_balance(db: DBSession, account_id: UUID, new_balance: Decimal) -> Account:
    account = db.get(Account, account_id)
    account.current_balance = new_balance
    db.flush()
    return account


def list_loans(
    db: DBSession,
) -> list[tuple[Account, LoanTerms, datetime | None]]:
    """Return active loan accounts with their terms and last import timestamp.

    INNER JOINs LoanTerms (every loan account must have terms — missing sidecar
    is a data integrity error, not a displayable state). Ordered by
    abs(current_balance) DESC (largest debt first).
    """
    last_import_subq = (
        db.query(
            ImportBatch.account_id,
            func.max(ImportBatch.created_at).label("last_import_at"),
        )
        .group_by(ImportBatch.account_id)
        .subquery()
    )

    rows = (
        db.query(Account, LoanTerms, last_import_subq.c.last_import_at)
        .join(LoanTerms, Account.id == LoanTerms.account_id)
        .outerjoin(last_import_subq, Account.id == last_import_subq.c.account_id)
        .filter(Account.is_active.is_(True))
        .filter(Account.type == "loan")
        .order_by(func.abs(Account.current_balance).desc())
        .all()
    )
    return list(rows)


def list_accounts_with_balances(
    db: DBSession,
) -> list[tuple[Account, datetime | None]]:
    """Return active non-credit accounts joined with their last import timestamp.

    Ordered by type ASC, display_name ASC. Credit accounts are excluded here
    because credit is not cash — that's business logic, not presentation logic.
    """
    last_import_subq = (
        db.query(
            ImportBatch.account_id,
            func.max(ImportBatch.created_at).label("last_import_at"),
        )
        .group_by(ImportBatch.account_id)
        .subquery()
    )

    rows = (
        db.query(Account, last_import_subq.c.last_import_at)
        .outerjoin(last_import_subq, Account.id == last_import_subq.c.account_id)
        .filter(Account.is_active.is_(True))
        .filter(Account.type != "credit")
        .order_by(Account.type, Account.display_name)
        .all()
    )
    return list(rows)
