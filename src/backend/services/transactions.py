from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from models.account import Account
from models.transaction import Transaction


@dataclass
class ReconciliationResult:
    ok: bool
    drift: Decimal
    computed: Decimal
    stored: Decimal


def reconcile(db: DBSession, account_id: UUID) -> ReconciliationResult:
    """Assert opening_balance + Σ(transactions.amount) == current_balance.

    Returns a ReconciliationResult; ok=False means a missing import or dropped row.
    """
    account = db.get(Account, account_id)
    total = db.query(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).filter(
        Transaction.account_id == account_id
    ).scalar()

    computed = account.opening_balance + total
    drift = computed - account.current_balance
    return ReconciliationResult(
        ok=drift == Decimal("0"),
        drift=drift,
        computed=computed,
        stored=account.current_balance,
    )


def recategorise(db: DBSession, transaction_id: UUID, category_id: int | None, user_id: UUID) -> Transaction:
    """Update a transaction's category and write an audit_log entry."""
    from services.auditing import record

    txn = db.get(Transaction, transaction_id)
    old_category_id = txn.category_id
    txn.category_id = category_id
    db.flush()

    record(
        db,
        action="recategorise",
        target_type="transaction",
        target_id=str(transaction_id),
        user_id=user_id,
        detail={"from": old_category_id, "to": category_id},
    )
    return txn
