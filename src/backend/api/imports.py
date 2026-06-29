"""Import routes — thin router; all logic lives in services/import_engine.py."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session as DBSession

from core.deps import get_current_user, get_db
from models.account import Account
from models.import_batch import ImportBatch
from models.user import User
from schemas.imports import ImportHistoryItem, ImportResponse, PreviewResponse
from services import flagging
from services.import_engine import ImportValidationError, preview_import, run_import

router = APIRouter(prefix="/imports", tags=["imports"])


def _decode_upload(content_bytes: bytes) -> str:
    try:
        return content_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "parse_error", "detail": f"File must be UTF-8: {exc}"},
        )


@router.post("/preview", response_model=PreviewResponse)
async def preview_csv(
    file: UploadFile,
    account_id: uuid.UUID | None = Query(default=None),
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    content = _decode_upload(await file.read())
    try:
        result = preview_import(
            db,
            content=content,
            filename=file.filename or "",
            account_id=account_id,
        )
    except ImportValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": exc.error_code, "detail": exc.detail},
        )
    return PreviewResponse(
        account_id=result.account_id,
        account_display_name=result.account_display_name,
        bank_code=result.bank_code,
        account_code=result.account_code,
        txn_date_min=result.txn_date_min,
        txn_date_max=result.txn_date_max,
        rows_found=result.rows_found,
        rows_to_add=result.rows_to_add,
        rows_duplicate=result.rows_duplicate,
        filename_seen_before=result.filename_seen_before,
        filename_seen_at=result.filename_seen_at,
    )


@router.post("/confirm", response_model=ImportResponse)
async def confirm_csv(
    file: UploadFile,
    account_id: uuid.UUID | None = Query(default=None),
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = _decode_upload(await file.read())
    try:
        result = run_import(
            db,
            content=content,
            filename=file.filename or "",
            user_id=current_user.id,
            account_id=account_id,
        )
    except ImportValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": exc.error_code, "detail": exc.detail},
        )
    db.commit()

    # Flagging runs in a separate transaction — a bug here must not roll back the import.
    try:
        flagging.run_for_import(db, import_id=result.import_id)
        db.commit()
    except Exception:
        db.rollback()

    return ImportResponse(
        import_id=result.import_id,
        rows_added=result.rows_added,
        rows_skipped=result.rows_skipped,
        reconciliation_ok=result.reconciliation_ok,
        drift=result.drift,
    )


@router.get("/history", response_model=list[ImportHistoryItem])
def get_history(
    limit: int = Query(default=10, ge=1, le=100),
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = (
        db.query(ImportBatch, Account.display_name)
        .join(Account, ImportBatch.account_id == Account.id)
        .order_by(ImportBatch.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        ImportHistoryItem(
            import_id=batch.id,
            filename=batch.filename,
            account_display_name=display_name,
            rows_added=batch.rows_added,
            rows_skipped=batch.rows_skipped,
            created_at=batch.created_at,
        )
        for batch, display_name in rows
    ]
