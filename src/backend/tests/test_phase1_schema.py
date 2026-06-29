"""
Phase 1 schema tests — prove the schema has teeth.

All tests cross the database seam directly (real Postgres, no mocks).
The conftest rollback fixture isolates each test.
"""
import datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from models.account import Account
from models.audit_log import AuditLog
from models.import_batch import ImportBatch
from models.lookups import AccountType, AuditAction, Bank
from models.transaction import Transaction
from services.accounts import MissingSidecarError, create_account
from services.transactions import recategorise, reconcile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_TXN_DATE = datetime.date(2024, 2, 1)
_AMOUNT = Decimal("-9.99")
_DESC = "SAMPLE GROCER 0000 SUBURB 00"
_BALANCE = Decimal("990.01")


@pytest.fixture
def seeds(db):
    """Minimal lookup seed rows every test needs."""
    db.add_all([
        Bank(code="bank_a", label="Bank A"),
        AccountType(code="transaction", label="Transaction"),
        AccountType(code="savings", label="Savings"),
        AccountType(code="loan", label="Loan"),
        AccountType(code="credit", label="Credit"),
        AuditAction(code="recategorise", label="Recategorise"),
    ])
    db.flush()


@pytest.fixture
def account(db, seeds, test_user):
    """A basic transaction account."""
    acct = Account(
        bank_code="bank_a",
        account_code="a1",
        display_name="Bank A Everyday",
        type="transaction",
        opening_balance=Decimal("3000.00"),
        current_balance=Decimal("3000.00"),
    )
    db.add(acct)
    db.flush()
    return acct


@pytest.fixture
def import_batch(db, account, test_user):
    batch = ImportBatch(
        user_id=test_user.id,
        filename="20240201_bank_a_a1.csv",
        bank_code="bank_a",
        account_id=account.id,
        rows_added=1,
        rows_skipped=0,
    )
    db.add(batch)
    db.flush()
    return batch


def _txn(account_id, import_id, **overrides):
    """Build a Transaction with the shared dedupe-key values, overridable per test."""
    fields = dict(
        account_id=account_id,
        import_id=import_id,
        txn_date=_TXN_DATE,
        amount=_AMOUNT,
        description_raw=_DESC,
        balance=_BALANCE,
    )
    fields.update(overrides)
    return Transaction(**fields)


# ---------------------------------------------------------------------------
# 1. TRACER BULLET — account insert returns Decimal money values
# ---------------------------------------------------------------------------


def test_account_insert(db, account):
    """Money columns return Decimal, not float."""
    fetched = db.get(Account, account.id)
    assert fetched is not None
    assert fetched.opening_balance == Decimal("3000.00")
    assert isinstance(fetched.opening_balance, Decimal)
    assert fetched.display_name == "Bank A Everyday"
    assert fetched.is_active is True


# ---------------------------------------------------------------------------
# 2. Duplicate insert is rejected (the keystone)
# ---------------------------------------------------------------------------


def test_duplicate_insert_rejected(db, account, import_batch):
    """The UNIQUE dedupe key rejects a second row identical on all five key columns."""
    db.add(_txn(account.id, import_batch.id))
    db.flush()

    db.add(_txn(account.id, import_batch.id))
    with pytest.raises(IntegrityError):
        db.flush()


# ---------------------------------------------------------------------------
# 3. Near-duplicate (different balance) is accepted
# ---------------------------------------------------------------------------


def test_near_duplicate_accepted(db, account, import_batch):
    """Two rows identical except balance are both accepted — balance is a true key member."""
    db.add(_txn(account.id, import_batch.id, balance=Decimal("990.01")))
    db.add(_txn(account.id, import_batch.id, balance=Decimal("980.02")))
    db.flush()  # no IntegrityError


# ---------------------------------------------------------------------------
# 4. NULL in any key column is rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("null_field", ["txn_date", "amount", "description_raw", "balance"])
def test_null_key_column_rejected(db, account, import_batch, null_field):
    """Every dedupe key column is NOT NULL — a NULL would silently defeat deduplication."""
    with pytest.raises(Exception):  # IntegrityError or StatementError
        db.add(_txn(account.id, import_batch.id, **{null_field: None}))
        db.flush()


# ---------------------------------------------------------------------------
# 5. NULL category_id is accepted (NULL = Uncategorised)
# ---------------------------------------------------------------------------


def test_category_null_accepted(db, account, import_batch):
    """category_id = NULL is valid — it means Uncategorised, not a broken FK."""
    txn = _txn(account.id, import_batch.id, category_id=None)
    db.add(txn)
    db.flush()
    fetched = db.get(Transaction, txn.id)
    assert fetched.category_id is None


# ---------------------------------------------------------------------------
# 7. Reconciliation closes on clean data
# ---------------------------------------------------------------------------


def test_reconciliation_closes(db, account, import_batch):
    """opening_balance + Σtxns == current_balance when all imports are present."""
    # opening_balance = 3000.00; add two transactions that sum to -9.99
    db.add(_txn(account.id, import_batch.id, amount=Decimal("-9.99"), balance=Decimal("2990.01")))
    db.flush()
    # Update current_balance to match the final row's balance
    account.current_balance = Decimal("2990.01")
    db.flush()

    result = reconcile(db, account.id)
    assert result.ok is True
    assert result.drift == Decimal("0.00")


# ---------------------------------------------------------------------------
# 8. Reconciliation detects drift (missing import / dropped row)
# ---------------------------------------------------------------------------


def test_reconciliation_detects_drift(db, account, import_batch):
    """When current_balance doesn't match opening_balance + Σtxns, drift is non-zero."""
    db.add(_txn(account.id, import_batch.id, amount=Decimal("-9.99"), balance=Decimal("2990.01")))
    db.flush()
    # current_balance left at 3000.00 (opening) — doesn't reflect the transaction
    result = reconcile(db, account.id)
    assert result.ok is False
    assert result.drift != Decimal("0.00")


# ---------------------------------------------------------------------------
# 9. Recategorise writes an audit_log entry (chain of custody)
# ---------------------------------------------------------------------------


def test_audit_on_recategorise(db, account, import_batch, test_user):
    """recategorise() must write exactly one audit_log row recording from/to."""
    txn = _txn(account.id, import_batch.id)
    db.add(txn)
    db.flush()

    recategorise(db, txn.id, category_id=None, user_id=test_user.id)

    logs = db.query(AuditLog).filter(
        AuditLog.target_type == "transaction",
        AuditLog.target_id == str(txn.id),
    ).all()
    assert len(logs) == 1
    assert logs[0].action == "recategorise"
    assert logs[0].user_id == test_user.id


# ---------------------------------------------------------------------------
# 6. Loan account without loan_terms is rejected at the service layer
# ---------------------------------------------------------------------------


def test_loan_without_terms_rejected(db, seeds, test_user):
    """create_account enforces that a loan account must have loan_terms."""
    with pytest.raises(MissingSidecarError):
        create_account(
            db,
            bank_code="bank_a",
            account_code="b2",
            display_name="Home Loan",
            type="loan",
            opening_balance=Decimal("-350000.00"),
            current_balance=Decimal("-350000.00"),
            created_by_user_id=test_user.id,
            # loan_terms intentionally omitted
        )
