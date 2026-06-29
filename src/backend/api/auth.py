from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DBSession

from core.config import settings
from core.deps import get_current_user, get_db
from core.limiter import limiter
from models.user import User
from schemas.auth import ChangePasswordRequest, LoginRequest, UserResponse
from services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_SESSION_COOKIE = "session"


@router.post("/login")
@limiter.limit(settings.login_rate_limit)
def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: DBSession = Depends(get_db),
):
    user = auth_service.authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth_service.create_session(db, user.id)
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days in seconds; matches default SESSION_EXPIRE_HOURS
    )
    return {"user": UserResponse.model_validate(user).model_dump()}


@router.post("/logout")
def logout(
    response: Response,
    token: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
    db: DBSession = Depends(get_db),
):
    if token:
        auth_service.delete_session(db, token)
    response.delete_cookie(_SESSION_COOKIE)
    return {"ok": True}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = auth_service.change_password(db, current_user, body.old_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
