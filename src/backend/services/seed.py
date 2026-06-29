"""Seed loader — loads fixtures/seed/*.json into the DB for dev and test.

Dev only. Never runs in production.
"""
import datetime
import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from models.budget import Budget
from models.category import Category
from models.rule import Rule
from services.accounts import create_account

_SEED_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "seed"


def load_fixtures(db: DBSession, *, user_id: UUID) -> None:
    """Load accounts, categories, and rules from fixtures/seed/ into db.

    Categories must exist before rules (FK). Both exist before accounts are
    queried for their category mappings, so the order here is intentional.
    """
    _load_categories(db, user_id=user_id)
    _load_rules(db, user_id=user_id)
    _load_accounts(db, user_id=user_id)
    db.flush()


def _load_categories(db: DBSession, *, user_id: UUID) -> None:
    data = json.loads((_SEED_DIR / "categories.json").read_text())
    today = datetime.date.today()
    valid_from = today.replace(day=1)
    for entry in data:
        cat = Category(name=entry["name"])
        db.add(cat)
        db.flush()
        if entry.get("budget") is not None:
            db.add(Budget(
                category_id=cat.id,
                valid_from=valid_from,
                amount=Decimal(entry["budget"]),
                created_by=user_id,
            ))
    db.flush()


def _load_rules(db: DBSession, *, user_id: UUID) -> None:
    data = json.loads((_SEED_DIR / "rules.json").read_text())
    cat_by_name = {c.name: c.id for c in db.query(Category).all()}
    for entry in data:
        db.add(Rule(
            match_type="contains",
            match_value=entry["match"],
            category_id=cat_by_name[entry["category"]],
            priority=100,
            created_by=user_id,
        ))
    db.flush()


def _load_accounts(db: DBSession, *, user_id: UUID) -> None:
    data = json.loads((_SEED_DIR / "accounts.json").read_text())
    for entry in data:
        opening = Decimal(entry["opening_balance"])
        loan_terms = None
        credit_terms = None
        if entry["type"] == "loan":
            loan_terms = {
                "original_principal": Decimal(entry["original_amount"]),
                "interest_rate": Decimal(entry["interest_rate"]),
                "term_months": int(entry["term_months"]),
            }
        if entry["type"] == "credit":
            credit_terms = {"credit_limit": Decimal(entry["credit_limit"])}
        create_account(
            db,
            bank_code=entry["bank"],
            account_code=entry["code"],
            display_name=entry["display_name"],
            type=entry["type"],
            opening_balance=opening,
            current_balance=opening,
            created_by_user_id=user_id,
            bank_account_name=entry.get("bank_account_name"),
            loan_terms=loan_terms,
            credit_terms=credit_terms,
        )
