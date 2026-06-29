"""
Test fixtures for the finance-app backend.

Requires a Postgres test database. Create it once (finance-app Postgres runs on 5433):
  docker-compose -f ops/deploy/docker-compose.yml exec db \
    createdb -U finance finance_test

Then run: uv run pytest  (from src/backend/)
"""
import os

# Set env vars before any app imports so Settings loads correctly.
os.environ.setdefault(
    "DATABASE_URL", "postgresql://finance:changeme@localhost:5433/finance_test"
)
os.environ.setdefault("LOGIN_RATE_LIMIT", "1000/minute")  # disable effective rate limit in tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401 — registers all models with Base.metadata
from core.database import Base
from core.deps import get_db
from core.security import hash_password
from main import app
from models.user import User

_TEST_DB_URL = os.environ["DATABASE_URL"]
_engine = create_engine(_TEST_DB_URL)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db(_create_tables):
    """Each test gets a transaction that is rolled back on teardown."""
    conn = _engine.connect()
    txn = conn.begin()
    session = _TestSession(bind=conn)
    yield session
    session.close()
    txn.rollback()
    conn.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        email="test@example.com",
        display_name="Test User",
        password_hash=hash_password("correct-password"),
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def db_with_lookups(db):
    """DB session pre-loaded with all lookup rows that migrations normally seed.

    Use this instead of bare `db` for Phase 2+ tests that need accounts,
    categories, rules, or the import pipeline.
    """
    from models.lookups import AccountType, AuditAction, Bank, FlagStatus, FlagType, MatchType

    db.add_all([
        Bank(code="bank_a", label="Bank A"),
        Bank(code="bank_b", label="Bank B"),
        AccountType(code="transaction", label="Transaction"),
        AccountType(code="savings", label="Savings"),
        AccountType(code="loan", label="Loan"),
        AccountType(code="credit", label="Credit"),
        MatchType(code="contains", label="Contains"),
        MatchType(code="equals", label="Equals"),
        MatchType(code="regex", label="Regex"),
        AuditAction(code="import", label="Import batch"),
        AuditAction(code="reverse_import", label="Reverse import"),
        AuditAction(code="recategorise", label="Recategorise transaction"),
        AuditAction(code="approve_flag", label="Approve flag"),
        AuditAction(code="dismiss_flag", label="Dismiss flag"),
        AuditAction(code="create_rule", label="Create rule"),
        FlagStatus(code="open", label="Open"),
        FlagStatus(code="approved", label="Approved"),
        FlagStatus(code="dismissed", label="Dismissed"),
        FlagType(code="over_threshold", label="Over threshold", description=None),
        FlagType(code="double_charge", label="Possible double charge", description=None),
        FlagType(code="new_merchant", label="New merchant", description=None),
        FlagType(code="recurring_change", label="Change in regular payment", description=None),
    ])
    db.flush()
    return db
