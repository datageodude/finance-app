import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class AccountSummary(BaseModel):
    id: uuid.UUID
    display_name: str
    bank_code: str
    account_code: str
    type: str


class AccountBalance(BaseModel):
    id: uuid.UUID
    display_name: str
    bank_code: str
    type: str
    current_balance: Decimal
    available_balance: Decimal | None
    last_import_at: datetime | None


class LoanDetail(BaseModel):
    id: uuid.UUID
    display_name: str
    bank_code: str
    balance_owing: Decimal          # abs(current_balance) — always positive
    available_balance: Decimal | None
    original_principal: Decimal
    interest_rate: Decimal
    term_months: int
    start_date: date | None
    end_date: date | None
    last_import_at: datetime | None
