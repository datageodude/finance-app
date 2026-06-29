import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class FlagItem(BaseModel):
    flag_id: int
    flag_type: str
    reason: str
    status: str
    created_at: datetime
    txn_id: uuid.UUID
    txn_date: date
    txn_amount: Decimal
    txn_description_raw: str
    account_display_name: str
    merchant_name: str | None
    related_txn_id: uuid.UUID | None
    related_txn_date: date | None
    related_txn_amount: Decimal | None


class ApproveRequest(BaseModel):
    custom_threshold: Decimal | None = None


class FlagActionResponse(BaseModel):
    flag_id: int
    status: str


class GenerateResponse(BaseModel):
    flags_created: int
