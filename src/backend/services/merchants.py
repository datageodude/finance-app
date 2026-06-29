"""Merchant service — lookup-or-create for the merchants table.

Called by the import engine (Phase 2) and the flagging engine (Phase 5).
Keeps the SELECT-then-INSERT-if-missing logic behind a single call so callers
never write that pattern directly.
"""
from sqlalchemy.orm import Session as DBSession

from models.merchant import Merchant


def get_or_create(db: DBSession, normalised_name: str) -> Merchant:
    """Return the Merchant with normalised_name, creating it if needed.

    Flushes on create (does not commit — caller owns the transaction boundary).
    """
    merchant = db.query(Merchant).filter_by(normalised_name=normalised_name).first()
    if merchant is not None:
        return merchant
    merchant = Merchant(normalised_name=normalised_name)
    db.add(merchant)
    db.flush()
    return merchant
