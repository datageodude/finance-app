"""Phase 2 — seed loader tests.

load_fixtures() must create all accounts, categories, and rules from
fixtures/seed/ so that import engine tests start with a complete dataset.
"""
from decimal import Decimal

from models.account import Account, LoanTerms
from models.category import Category
from models.rule import Rule
from services.seed import load_fixtures

# ---------------------------------------------------------------------------
# Tracer bullet: accounts are created
# ---------------------------------------------------------------------------


def test_load_fixtures_creates_all_accounts(db_with_lookups, test_user):
    load_fixtures(db_with_lookups, user_id=test_user.id)
    assert db_with_lookups.query(Account).count() == 5


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


def test_load_fixtures_creates_categories(db_with_lookups, test_user):
    load_fixtures(db_with_lookups, user_id=test_user.id)
    assert db_with_lookups.query(Category).count() == 11


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def test_load_fixtures_creates_rules(db_with_lookups, test_user):
    load_fixtures(db_with_lookups, user_id=test_user.id)
    assert db_with_lookups.query(Rule).count() == 18


# ---------------------------------------------------------------------------
# Loan account sidecar
# ---------------------------------------------------------------------------


def test_loan_account_has_terms(db_with_lookups, test_user):
    load_fixtures(db_with_lookups, user_id=test_user.id)
    b2 = db_with_lookups.query(Account).filter_by(account_code="b2").first()
    assert b2 is not None
    terms = db_with_lookups.get(LoanTerms, b2.id)
    assert terms is not None
    assert terms.interest_rate == Decimal("5.89")
    assert terms.term_months == 360
    assert terms.original_principal == Decimal("360000.00")
