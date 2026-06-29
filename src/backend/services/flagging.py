"""Flagging engine — generates and manages transaction flags.

Runs as a separate DB transaction from the import (caller's responsibility to commit).
Three v1 rules: over_threshold, double_charge, new_merchant.

Caller (the API router) is responsible for db.commit(). Same convention as import_engine.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session as DBSession

from models.account import Account
from models.flag import Flag
from models.import_batch import ImportBatch
from models.merchant import MerchantThresholdOverride
from models.transaction import Transaction
from services import auditing

# ---------------------------------------------------------------------------
# Config — read once at module load
# ---------------------------------------------------------------------------

_THRESHOLD = Decimal(os.environ.get("FLAG_THRESHOLD", "100.00"))
_DOUBLE_CHARGE_DAYS = int(os.environ.get("DOUBLE_CHARGE_DAYS", "7"))

_FLAGGABLE_ACCOUNT_TYPES = {"transaction", "credit"}


# ---------------------------------------------------------------------------
# Public data shapes
# ---------------------------------------------------------------------------


@dataclass
class FlagResult:
    flags_created: int


@dataclass
class FlagDetail:
    flag_id: int
    flag_type: str
    reason: str
    status: str
    created_at: datetime
    txn_id: UUID
    txn_date: date
    txn_amount: Decimal
    txn_description_raw: str
    account_display_name: str
    merchant_name: str | None
    related_txn_id: UUID | None
    related_txn_date: date | None
    related_txn_amount: Decimal | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_for_import(db: DBSession, *, import_id: UUID) -> FlagResult:
    """Generate flags for all transactions in one import batch."""
    txns = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .join(ImportBatch, Transaction.import_id == ImportBatch.id)
        .filter(ImportBatch.id == import_id)
        .all()
    )
    return _generate_flags(db, txns)


def generate_for_account(db: DBSession, *, account_id: UUID) -> FlagResult:
    """Generate flags for all transactions on an account (backfill)."""
    txns = (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .all()
    )
    return _generate_flags(db, txns)


def list_open_flags(db: DBSession) -> list[FlagDetail]:
    """Return all open flags with full transaction context, newest first."""
    from sqlalchemy.orm import aliased

    from models.merchant import Merchant
    RelatedAlias = aliased(Transaction)

    rows = (
        db.query(
            Flag,
            Transaction,
            Account,
            Merchant,
            RelatedAlias,
        )
        .join(Transaction, Flag.transaction_id == Transaction.id)
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Merchant, Transaction.merchant_id == Merchant.id)
        .outerjoin(RelatedAlias, Flag.related_transaction_id == RelatedAlias.id)
        .filter(Flag.status == "open")
        .order_by(Flag.created_at.desc())
        .all()
    )

    return [
        FlagDetail(
            flag_id=flag.id,
            flag_type=flag.flag_type,
            reason=flag.reason,
            status=flag.status,
            created_at=flag.created_at,
            txn_id=txn.id,
            txn_date=txn.txn_date,
            txn_amount=txn.amount,
            txn_description_raw=txn.description_raw,
            account_display_name=account.display_name,
            merchant_name=merchant.normalised_name if merchant else None,
            related_txn_id=related.id if related else None,
            related_txn_date=related.txn_date if related else None,
            related_txn_amount=related.amount if related else None,
        )
        for flag, txn, account, merchant, related in rows
    ]


def approve_flag(
    db: DBSession,
    *,
    flag_id: int,
    user_id: UUID,
    custom_threshold: Decimal | None = None,
) -> None:
    """Approve a flag. Optionally sets a merchant threshold override."""
    flag = db.get(Flag, flag_id)
    if flag is None:
        raise ValueError(f"Flag {flag_id} not found")

    now = datetime.now(timezone.utc)
    flag.status = "approved"
    flag.resolved_by = user_id
    flag.resolved_at = now
    db.flush()

    if custom_threshold is not None and flag.flag_type == "over_threshold":
        _upsert_merchant_override(db, flag=flag, threshold=custom_threshold, user_id=user_id)

    auditing.record(
        db,
        action="approve_flag",
        target_type="flag",
        target_id=str(flag_id),
        user_id=user_id,
    )


def dismiss_flag(db: DBSession, *, flag_id: int, user_id: UUID) -> None:
    """Dismiss a flag (mark as noise)."""
    flag = db.get(Flag, flag_id)
    if flag is None:
        raise ValueError(f"Flag {flag_id} not found")

    now = datetime.now(timezone.utc)
    flag.status = "dismissed"
    flag.resolved_by = user_id
    flag.resolved_at = now
    db.flush()

    auditing.record(
        db,
        action="dismiss_flag",
        target_type="flag",
        target_id=str(flag_id),
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Private — flag generation
# ---------------------------------------------------------------------------


def _generate_flags(db: DBSession, txns: list[Transaction]) -> FlagResult:
    if not txns:
        return FlagResult(flags_created=0)

    overrides = _load_overrides(db)
    created = 0

    for txn in txns:
        account = db.get(Account, txn.account_id)
        created += _check_over_threshold(db, txn, account, overrides)
        created += _check_double_charge(db, txn, account)
        created += _check_new_merchant(db, txn, account)

    return FlagResult(flags_created=created)


def _load_overrides(db: DBSession) -> dict[int, Decimal]:
    """Load all merchant threshold overrides into a dict keyed by merchant_id."""
    rows = db.query(MerchantThresholdOverride).all()
    return {r.merchant_id: r.threshold for r in rows}


def _insert_flag(
    db: DBSession,
    *,
    transaction_id: UUID,
    flag_type: str,
    reason: str,
    related_transaction_id: UUID | None = None,
) -> int:
    """Insert a flag using ON CONFLICT DO NOTHING. Returns 1 if inserted, 0 if skipped."""
    stmt = (
        pg_insert(Flag)
        .values(
            transaction_id=transaction_id,
            flag_type=flag_type,
            reason=reason,
            status="open",
            related_transaction_id=related_transaction_id,
        )
        .on_conflict_do_nothing(constraint="uq_flags_txn_flag_type")
    )
    result = db.execute(stmt)
    db.flush()
    return result.rowcount


def _check_over_threshold(
    db: DBSession,
    txn: Transaction,
    account: Account,
    overrides: dict[int, Decimal],
) -> int:
    if account.type not in _FLAGGABLE_ACCOUNT_TYPES:
        return 0
    if txn.amount >= Decimal("0"):
        return 0

    threshold = overrides.get(txn.merchant_id, _THRESHOLD) if txn.merchant_id else _THRESHOLD
    debit = abs(txn.amount)

    if debit <= threshold:
        return 0

    reason = f"Debit of ${debit:.2f} exceeds threshold of ${threshold:.2f}"
    return _insert_flag(db, transaction_id=txn.id, flag_type="over_threshold", reason=reason)


def _check_double_charge(
    db: DBSession,
    txn: Transaction,
    account: Account,
) -> int:
    if txn.merchant_id is None:
        return 0

    from datetime import timedelta
    window_start = txn.txn_date - timedelta(days=_DOUBLE_CHARGE_DAYS)

    earlier = (
        db.query(Transaction)
        .filter(
            Transaction.account_id == txn.account_id,
            Transaction.merchant_id == txn.merchant_id,
            Transaction.amount == txn.amount,
            Transaction.txn_date >= window_start,
            Transaction.txn_date < txn.txn_date,
            Transaction.id != txn.id,
        )
        .order_by(Transaction.txn_date.asc())
        .first()
    )

    if earlier is None:
        return 0

    from models.merchant import Merchant
    merchant = db.get(Merchant, txn.merchant_id)
    name = merchant.normalised_name if merchant else "this merchant"
    reason = (
        f"Possible double charge: ${abs(txn.amount):.2f} at {name} "
        f"also charged on {earlier.txn_date.strftime('%d %b %Y')}"
    )
    return _insert_flag(
        db,
        transaction_id=txn.id,
        flag_type="double_charge",
        reason=reason,
        related_transaction_id=earlier.id,
    )


def _check_new_merchant(
    db: DBSession,
    txn: Transaction,
    account: Account,
) -> int:
    if txn.merchant_id is None:
        return 0

    first_seen: date | None = (
        db.query(func.min(Transaction.txn_date))
        .filter(Transaction.merchant_id == txn.merchant_id)
        .scalar()
    )

    if first_seen is None or first_seen != txn.txn_date:
        return 0

    from models.merchant import Merchant
    merchant = db.get(Merchant, txn.merchant_id)
    name = merchant.normalised_name if merchant else "unknown"
    reason = f"First transaction at {name}"
    return _insert_flag(db, transaction_id=txn.id, flag_type="new_merchant", reason=reason)


# ---------------------------------------------------------------------------
# Private — merchant threshold override upsert
# ---------------------------------------------------------------------------


def _upsert_merchant_override(
    db: DBSession,
    *,
    flag: Flag,
    threshold: Decimal,
    user_id: UUID,
) -> None:
    """Upsert a merchant_threshold_overrides row when approving an over_threshold flag."""
    txn = db.get(Transaction, flag.transaction_id)
    if txn is None or txn.merchant_id is None:
        return

    stmt = (
        pg_insert(MerchantThresholdOverride)
        .values(
            merchant_id=txn.merchant_id,
            threshold=threshold,
            created_by=user_id,
        )
        .on_conflict_do_update(
            index_elements=["merchant_id"],
            set_={"threshold": threshold, "created_by": user_id},
        )
    )
    db.execute(stmt)
    db.flush()
