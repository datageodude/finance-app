"""Phase 2 — import engine integration tests.

All tests hit the real Postgres DB (no mocks) via the seeded fixture, which
provides the full fixture corpus (5 accounts, 11 categories, 18 rules).

Test order follows the spec test plan:
  1. Bank A full import (tracer bullet)
  2. Bank B full import
  3. Idempotency — re-import same file → 0 new rows
  4. Partial overlap — March file after Feb → adds exactly 2 rows
  5. Uncategorised — unknown payee → category_id = None
  6. Merchant reuse — same merchant across two imports → one merchants row
  7. Error cases — bad filename, unknown account
"""
from decimal import Decimal
from pathlib import Path

import pytest

from models.account import Account
from models.audit_log import AuditLog
from models.merchant import Merchant
from models.transaction import Transaction
from services.import_engine import ImportValidationError, run_import
from services.seed import load_fixtures

_IMPORTS_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "imports"


def _read(filename: str) -> str:
    return (_IMPORTS_DIR / filename).read_text()


@pytest.fixture
def seeded(db_with_lookups, test_user):
    """DB loaded with the full fixture corpus (accounts, categories, rules)."""
    load_fixtures(db_with_lookups, user_id=test_user.id)
    return db_with_lookups


def _import(db, filename, user_id):
    return run_import(db, content=_read(filename), filename=filename, user_id=user_id)


# ---------------------------------------------------------------------------
# 1. Bank A full import — tracer bullet
# ---------------------------------------------------------------------------


def test_bank_a_import_row_count(seeded, test_user):
    result = _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    assert result.rows_added == 43
    assert result.rows_skipped == 0


def test_bank_a_import_reconciliation_ok(seeded, test_user):
    result = _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    assert result.reconciliation_ok is True
    assert result.drift == Decimal("0.00")


def test_bank_a_import_updates_current_balance(seeded, test_user):
    _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    account = seeded.query(Account).filter_by(account_code="a1").first()
    assert account.current_balance == Decimal("3988.76")


def test_bank_a_import_writes_audit_log(seeded, test_user):
    result = _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    log = seeded.query(AuditLog).filter_by(
        action="import", target_type="import", target_id=str(result.import_id)
    ).first()
    assert log is not None
    assert log.user_id == test_user.id


def test_bank_a_sign_convention(seeded, test_user):
    """All debit amounts stored as negative — the locked sign convention."""
    _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    txn = seeded.query(Transaction).filter_by(
        description_raw="POS (Cr) purchase100021_SAMPLE GROCER *METRO"
    ).first()
    assert txn is not None
    assert txn.amount == Decimal("-85.40")


# ---------------------------------------------------------------------------
# 2. Bank B full import
# ---------------------------------------------------------------------------


def test_bank_b_import_row_count(seeded, test_user):
    result = _import(seeded, "20240229_bank_b_b1.csv", test_user.id)
    assert result.rows_added == 15


def test_bank_b_import_reconciliation_ok(seeded, test_user):
    result = _import(seeded, "20240229_bank_b_b1.csv", test_user.id)
    assert result.reconciliation_ok is True


def test_bank_b_debit_stored_as_negative(seeded, test_user):
    """Bank B Debit column converted to negative amount — sign convention."""
    _import(seeded, "20240229_bank_b_b1.csv", test_user.id)
    txn = seeded.query(Transaction).filter_by(
        description_raw="FRESH MART 0291 SUBURB 02"
    ).first()
    assert txn is not None
    assert txn.amount == Decimal("-72.10")


def test_bank_b_description_raw_is_original_description(seeded, test_user):
    """description_raw comes from Original Description (raw), not Details (cleaned)."""
    _import(seeded, "20240229_bank_b_b1.csv", test_user.id)
    txn = seeded.query(Transaction).filter_by(
        description_raw="FRESH MART 0291 SUBURB 02"
    ).first()
    assert txn is not None


# ---------------------------------------------------------------------------
# 3. Idempotency — re-import same file → 0 new rows
# ---------------------------------------------------------------------------


def test_idempotency_no_new_rows(seeded, test_user):
    _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    result2 = _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    assert result2.rows_added == 0
    assert result2.rows_skipped == 43


# ---------------------------------------------------------------------------
# 4. Partial overlap — March file after Feb → adds exactly 2 rows
# ---------------------------------------------------------------------------


def test_partial_overlap_adds_two_rows(seeded, test_user):
    _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    result = _import(seeded, "20240307_bank_a_a1.csv", test_user.id)
    assert result.rows_added == 2
    assert result.rows_skipped == 3


# ---------------------------------------------------------------------------
# 5. Uncategorised — ABC123 UNKNOWN PAYEE → category_id = None
# ---------------------------------------------------------------------------


def test_uncategorised_row_has_null_category(seeded, test_user):
    _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    txn = seeded.query(Transaction).filter_by(
        description_raw="DIRECT DEBIT ABC123 UNKNOWN PAYEE"
    ).first()
    assert txn is not None
    assert txn.category_id is None


# ---------------------------------------------------------------------------
# 6. Merchant reuse — same merchant across two imports → one merchants row
# ---------------------------------------------------------------------------


def test_merchant_reuse_no_duplicates(seeded, test_user):
    """Re-importing a file calls get_or_create repeatedly; merchant stays one row."""
    _import(seeded, "20240229_bank_a_a1.csv", test_user.id)
    _import(seeded, "20240307_bank_a_a1.csv", test_user.id)
    # SAMPLE CAFE *CBD appears in both Feb and March overlap rows
    merchants = seeded.query(Merchant).filter_by(
        normalised_name="Sample Cafe *Cbd"
    ).all()
    assert len(merchants) == 1


# ---------------------------------------------------------------------------
# 7. Error cases
# ---------------------------------------------------------------------------


def test_bad_filename_raises_validation_error(seeded, test_user):
    with pytest.raises(ImportValidationError) as exc_info:
        run_import(seeded, content="...", filename="bad.csv", user_id=test_user.id)
    assert exc_info.value.error_code == "bad_filename"


def test_unknown_account_raises_validation_error(seeded, test_user):
    with pytest.raises(ImportValidationError) as exc_info:
        run_import(
            seeded, content="...", filename="20240229_bank_a_zzz.csv", user_id=test_user.id
        )
    assert exc_info.value.error_code == "unknown_account"
