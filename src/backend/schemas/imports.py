import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ImportResponse(BaseModel):
    import_id: uuid.UUID
    rows_added: int
    rows_skipped: int
    reconciliation_ok: bool
    drift: Decimal


class ImportErrorResponse(BaseModel):
    error: str   # bad_filename | unknown_bank | unknown_account | parse_error
    detail: str


class PreviewResponse(BaseModel):
    account_id: uuid.UUID
    account_display_name: str
    bank_code: str
    account_code: str
    txn_date_min: date | None
    txn_date_max: date | None
    rows_found: int
    rows_to_add: int
    rows_duplicate: int
    filename_seen_before: bool
    filename_seen_at: datetime | None


class ImportHistoryItem(BaseModel):
    import_id: uuid.UUID
    filename: str
    account_display_name: str
    rows_added: int
    rows_skipped: int
    created_at: datetime
