"""Flags routes — thin router; all logic lives in services/flagging.py."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from core.deps import get_current_user, get_db
from models.user import User
from schemas.flags import ApproveRequest, FlagActionResponse, FlagItem, GenerateResponse
from services import flagging

router = APIRouter(prefix="/flags", tags=["flags"])


@router.get("", response_model=list[FlagItem])
def get_open_flags(
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return [FlagItem(**vars(f)) for f in flagging.list_open_flags(db)]


# POST /flags/generate must be declared before /{flag_id}/... routes to avoid
# "generate" being matched as an integer flag_id.
@router.post("/generate", response_model=GenerateResponse)
def generate_flags(
    account_id: uuid.UUID = Query(...),
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = flagging.generate_for_account(db, account_id=account_id)
    db.commit()
    return GenerateResponse(flags_created=result.flags_created)


@router.post("/{flag_id}/approve", response_model=FlagActionResponse)
def approve_flag(
    flag_id: int,
    body: ApproveRequest,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        flagging.approve_flag(
            db,
            flag_id=flag_id,
            user_id=current_user.id,
            custom_threshold=body.custom_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    db.commit()
    return FlagActionResponse(flag_id=flag_id, status="approved")


@router.post("/{flag_id}/dismiss", response_model=FlagActionResponse)
def dismiss_flag(
    flag_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        flagging.dismiss_flag(db, flag_id=flag_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    db.commit()
    return FlagActionResponse(flag_id=flag_id, status="dismissed")
