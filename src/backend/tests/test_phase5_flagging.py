"""Phase 5 — flagging engine integration tests.

All tests hit the real Postgres DB (no mocks). Test transactions are constructed
directly (not via the import engine) so flag rules are tested independently.

Test order:
  1. over_threshold — fires on debit exceeding threshold
  2. over_threshold — skips credits, loan/savings, merchant overrides
  3. double_charge — fires within window
  4. double_charge — skips NULL merchant and out-of-window pairs
  5. new_merchant — fires on first transaction at a merchant
  6. new_merchant — skips known merchant and NULL merchant
  7. Idempotency — no duplicate flags on re-run
  8. approve_flag / dismiss_flag — status, audit log, optional override
  9. list_open_flags — rich context, open-only
"""
import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("FLAG_THRESHOLD", "100.00")
os.environ.setdefault("DOUBLE_CHARGE_DAYS", "7")


from models.account import Account
from models.audit_log import AuditLog
from models.flag import Flag
from models.import_batch import ImportBatch
from models.merchant import Merchant, MerchantThresholdOverride
from models.transaction import Transaction
from services import flagging

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _account(db, type_="transaction", code="a1"):
    a = Account(
        bank_code="bank_a",
        account_code=code,
        display_name=f"Account {code}",
        type=type_,
        opening_balance=Decimal("1000.00"),
        current_balance=Decimal("1000.00"),
    )
    db.add(a)
    db.flush()
    return a


def _import_batch(db, user_id, account):
    ib = ImportBatch(
        user_id=user_id,
        filename=f"20240101_bank_a_{account.account_code}.csv",
        bank_code="bank_a",
        account_id=account.id,
        rows_added=1,
        rows_skipped=0,
    )
    db.add(ib)
    db.flush()
    return ib


def _merchant(db, name="Test Merchant"):
    m = Merchant(normalised_name=name)
    db.add(m)
    db.flush()
    return m


def _txn(
    db,
    account,
    import_batch,
    *,
    amount,
    merchant=None,
    txn_date=date(2024, 1, 15),
    description="TEST TXN",
    balance=Decimal("900.00"),
):
    t = Transaction(
        account_id=account.id,
        import_id=import_batch.id,
        txn_date=txn_date,
        amount=amount,
        description_raw=description,
        balance=balance,
        merchant_id=merchant.id if merchant else None,
    )
    db.add(t)
    db.flush()
    return t


# ---------------------------------------------------------------------------
# 1. over_threshold — fires on debit exceeding threshold
# ---------------------------------------------------------------------------


def test_over_threshold_fires_on_debit(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db)
    _txn(db, acc, ib, amount=Decimal("-150.00"), merchant=merchant)

    result = flagging.run_for_import(db, import_id=ib.id)

    flags = db.query(Flag).filter_by(flag_type="over_threshold").all()
    assert result.flags_created >= 1
    assert len(flags) == 1
    assert "150" in flags[0].reason


def test_over_threshold_skips_below_threshold(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-50.00"))

    flagging.run_for_import(db, import_id=ib.id)

    flags = db.query(Flag).filter_by(flag_type="over_threshold").all()
    assert len(flags) == 0


def test_over_threshold_skips_credits(db_with_lookups, test_user):
    """Positive amounts (income/deposits) never trigger over_threshold."""
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("500.00"))

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="over_threshold").count() == 0


def test_over_threshold_skips_loan_accounts(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db, type_="loan", code="l1")
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-2500.00"))

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="over_threshold").count() == 0


def test_over_threshold_skips_savings_accounts(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db, type_="savings", code="s1")
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-500.00"))

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="over_threshold").count() == 0


def test_over_threshold_fires_on_credit_accounts(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db, type_="credit", code="c1")
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-200.00"))

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="over_threshold").count() == 1


def test_over_threshold_respects_merchant_override(db_with_lookups, test_user):
    """Merchant with override threshold 300 — debit of 150 should not flag."""
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Mortgage Bank")
    _txn(db, acc, ib, amount=Decimal("-150.00"), merchant=merchant)
    override = MerchantThresholdOverride(
        merchant_id=merchant.id,
        threshold=Decimal("300.00"),
        created_by=test_user.id,
    )
    db.add(override)
    db.flush()

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="over_threshold").count() == 0


def test_over_threshold_override_still_flags_above_custom(db_with_lookups, test_user):
    """Override threshold 200 — debit of 500 should still flag."""
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Mortgage Bank")
    _txn(db, acc, ib, amount=Decimal("-500.00"), merchant=merchant)
    override = MerchantThresholdOverride(
        merchant_id=merchant.id,
        threshold=Decimal("200.00"),
        created_by=test_user.id,
    )
    db.add(override)
    db.flush()

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="over_threshold").count() == 1


# ---------------------------------------------------------------------------
# 2. double_charge — fires within window
# ---------------------------------------------------------------------------


def test_double_charge_fires_within_window(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Coffee Shop")
    earlier = _txn(db, acc, ib, amount=Decimal("-12.50"), merchant=merchant,
                   txn_date=date(2024, 1, 10), description="COFFEE SHOP", balance=Decimal("990.00"))
    later = _txn(db, acc, ib, amount=Decimal("-12.50"), merchant=merchant,
                 txn_date=date(2024, 1, 14), description="COFFEE SHOP", balance=Decimal("977.50"))

    flagging.run_for_import(db, import_id=ib.id)

    flags = db.query(Flag).filter_by(flag_type="double_charge").all()
    assert len(flags) == 1
    assert flags[0].transaction_id == later.id
    assert flags[0].related_transaction_id == earlier.id


def test_double_charge_skips_outside_window(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Weekly Shop")
    _txn(db, acc, ib, amount=Decimal("-55.00"), merchant=merchant,
         txn_date=date(2024, 1, 1), description="WEEKLY SHOP 1", balance=Decimal("945.00"))
    _txn(db, acc, ib, amount=Decimal("-55.00"), merchant=merchant,
         txn_date=date(2024, 1, 10), description="WEEKLY SHOP 2", balance=Decimal("890.00"))

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="double_charge").count() == 0


def test_double_charge_skips_null_merchant(db_with_lookups, test_user):
    """Same amount, NULL merchant (internal transfer) — must not flag."""
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-500.00"), merchant=None,
         txn_date=date(2024, 1, 10), description="TRANSFER OUT", balance=Decimal("500.00"))
    _txn(db, acc, ib, amount=Decimal("-500.00"), merchant=None,
         txn_date=date(2024, 1, 12), description="TRANSFER OUT 2", balance=Decimal("0.00"))

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="double_charge").count() == 0


# ---------------------------------------------------------------------------
# 3. new_merchant — fires on first transaction at a merchant
# ---------------------------------------------------------------------------


def test_new_merchant_fires_on_first_transaction(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Brand New Store")
    txn = _txn(db, acc, ib, amount=Decimal("-35.00"), merchant=merchant)

    flagging.run_for_import(db, import_id=ib.id)

    flags = db.query(Flag).filter_by(flag_type="new_merchant").all()
    assert len(flags) == 1
    assert flags[0].transaction_id == txn.id
    assert "Brand New Store" in flags[0].reason


def test_new_merchant_skips_known_merchant(db_with_lookups, test_user):
    """Merchant with an earlier transaction — not flagged as new."""
    db = db_with_lookups
    acc = _account(db)
    ib_old = _import_batch(db, test_user.id, acc)
    ib_new = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Known Store")
    # Earlier transaction in a prior import
    _txn(db, acc, ib_old, amount=Decimal("-20.00"), merchant=merchant,
         txn_date=date(2023, 12, 1), description="KNOWN STORE OLD", balance=Decimal("980.00"))
    # New transaction in this import
    _txn(db, acc, ib_new, amount=Decimal("-25.00"), merchant=merchant,
         txn_date=date(2024, 1, 15), description="KNOWN STORE NEW", balance=Decimal("955.00"))

    flagging.run_for_import(db, import_id=ib_new.id)

    assert db.query(Flag).filter_by(flag_type="new_merchant").count() == 0


def test_new_merchant_skips_null_merchant(db_with_lookups, test_user):
    """Internal transfers (NULL merchant) never trigger new_merchant."""
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-100.00"), merchant=None, description="TRANSFER")

    flagging.run_for_import(db, import_id=ib.id)

    assert db.query(Flag).filter_by(flag_type="new_merchant").count() == 0


# ---------------------------------------------------------------------------
# 4. Idempotency
# ---------------------------------------------------------------------------


def test_no_duplicate_flags_on_rerun(db_with_lookups, test_user):
    """Running flagging twice on the same import produces no duplicate flags."""
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Big Store")
    _txn(db, acc, ib, amount=Decimal("-200.00"), merchant=merchant)

    flagging.run_for_import(db, import_id=ib.id)
    flagging.run_for_import(db, import_id=ib.id)  # second run — should be a no-op

    assert db.query(Flag).filter_by(flag_type="over_threshold").count() == 1
    assert db.query(Flag).filter_by(flag_type="new_merchant").count() == 1


# ---------------------------------------------------------------------------
# 5. approve_flag / dismiss_flag
# ---------------------------------------------------------------------------


def test_approve_flag_sets_status(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-150.00"))
    flagging.run_for_import(db, import_id=ib.id)

    flag = db.query(Flag).filter_by(flag_type="over_threshold").first()
    flagging.approve_flag(db, flag_id=flag.id, user_id=test_user.id)

    db.expire(flag)
    assert flag.status == "approved"
    assert flag.resolved_by == test_user.id
    assert flag.resolved_at is not None


def test_approve_flag_writes_audit_log(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-150.00"))
    flagging.run_for_import(db, import_id=ib.id)

    flag = db.query(Flag).filter_by(flag_type="over_threshold").first()
    flagging.approve_flag(db, flag_id=flag.id, user_id=test_user.id)

    log = db.query(AuditLog).filter_by(action="approve_flag").first()
    assert log is not None
    assert log.user_id == test_user.id


def test_dismiss_flag_sets_status(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib, amount=Decimal("-150.00"))
    flagging.run_for_import(db, import_id=ib.id)

    flag = db.query(Flag).filter_by(flag_type="over_threshold").first()
    flagging.dismiss_flag(db, flag_id=flag.id, user_id=test_user.id)

    db.expire(flag)
    assert flag.status == "dismissed"
    assert flag.resolved_by == test_user.id
    assert flag.resolved_at is not None


def test_approve_with_custom_threshold_creates_override(db_with_lookups, test_user):
    """Approving an over_threshold flag with custom_threshold upserts an override row."""
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Mortgage Co")
    _txn(db, acc, ib, amount=Decimal("-2500.00"), merchant=merchant)
    flagging.run_for_import(db, import_id=ib.id)

    flag = db.query(Flag).filter_by(flag_type="over_threshold").first()
    flagging.approve_flag(db, flag_id=flag.id, user_id=test_user.id,
                          custom_threshold=Decimal("3000.00"))

    override = db.query(MerchantThresholdOverride).filter_by(merchant_id=merchant.id).first()
    assert override is not None
    assert override.threshold == Decimal("3000.00")
    assert override.created_by == test_user.id


def test_approve_without_custom_threshold_no_override(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Regular Store")
    _txn(db, acc, ib, amount=Decimal("-150.00"), merchant=merchant)
    flagging.run_for_import(db, import_id=ib.id)

    flag = db.query(Flag).filter_by(flag_type="over_threshold").first()
    flagging.approve_flag(db, flag_id=flag.id, user_id=test_user.id)

    assert db.query(MerchantThresholdOverride).count() == 0


# ---------------------------------------------------------------------------
# 6. list_open_flags
# ---------------------------------------------------------------------------


def test_list_open_flags_returns_open_only(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db, code="a1")
    acc2 = _account(db, code="a2")
    ib = _import_batch(db, test_user.id, acc)
    ib2 = _import_batch(db, test_user.id, acc2)
    merchant = _merchant(db, "Shop A")
    _txn(db, acc, ib, amount=Decimal("-200.00"), merchant=merchant)
    _txn(db, acc2, ib2, amount=Decimal("-300.00"))
    flagging.run_for_import(db, import_id=ib.id)
    flagging.run_for_import(db, import_id=ib2.id)

    # Dismiss one flag
    flag_to_dismiss = db.query(Flag).filter_by(flag_type="over_threshold",
                                                status="open").first()
    flagging.dismiss_flag(db, flag_id=flag_to_dismiss.id, user_id=test_user.id)

    open_flags = flagging.list_open_flags(db)

    assert all(f.status == "open" for f in open_flags)
    dismissed_ids = {flag_to_dismiss.id}
    assert all(f.flag_id not in dismissed_ids for f in open_flags)


def test_list_open_flags_includes_context(db_with_lookups, test_user):
    db = db_with_lookups
    acc = _account(db)
    ib = _import_batch(db, test_user.id, acc)
    merchant = _merchant(db, "Context Store")
    _txn(db, acc, ib, amount=Decimal("-150.00"), merchant=merchant,
         description="CONTEXT STORE TXN")
    flagging.run_for_import(db, import_id=ib.id)

    open_flags = flagging.list_open_flags(db)
    flag = next(f for f in open_flags if f.flag_type == "over_threshold")

    assert flag.account_display_name == acc.display_name
    assert flag.merchant_name == "Context Store"
    assert flag.txn_amount == Decimal("-150.00")


def test_generate_for_account_backfills(db_with_lookups, test_user):
    """generate_for_account runs across all transactions on an account."""
    db = db_with_lookups
    acc = _account(db)
    ib1 = _import_batch(db, test_user.id, acc)
    ib2 = _import_batch(db, test_user.id, acc)
    _txn(db, acc, ib1, amount=Decimal("-200.00"), description="TXN1", balance=Decimal("800.00"))
    _txn(db, acc, ib2, amount=Decimal("-300.00"), description="TXN2", balance=Decimal("500.00"))

    result = flagging.generate_for_account(db, account_id=acc.id)

    assert result.flags_created == 2
    assert db.query(Flag).filter_by(flag_type="over_threshold").count() == 2
