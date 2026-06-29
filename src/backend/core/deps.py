from typing import Generator

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from core.database import SessionLocal


def get_db() -> Generator[DBSession, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str | None = Cookie(default=None, alias="session"),
    db: DBSession = Depends(get_db),
):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from models.user import User
    from services.auth import get_session

    session = get_session(db, token)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
