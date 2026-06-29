from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as DBSession

from core.config import settings
from core.security import generate_session_token, hash_password, verify_password
from models.session import Session
from models.user import User


def authenticate_user(db: DBSession, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    if user.mfa_secret:
        # MFA hook — seam exists; active when mfa_secret is populated (Phase 7)
        pass
    return user


def create_session(db: DBSession, user_id) -> str:
    token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_expire_hours)
    session = Session(token=token, user_id=user_id, expires_at=expires_at)
    db.add(session)
    db.commit()
    return token


def get_session(db: DBSession, token: str) -> Session | None:
    session = db.query(Session).filter(Session.token == token).first()
    if not session:
        return None
    if session.expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    # Sliding expiry: reset on each use
    session.expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.session_expire_hours
    )
    db.commit()
    return session


def delete_session(db: DBSession, token: str) -> None:
    db.query(Session).filter(Session.token == token).delete()
    db.commit()


def change_password(db: DBSession, user: User, old_password: str, new_password: str) -> bool:
    if not verify_password(old_password, user.password_hash):
        return False
    user.password_hash = hash_password(new_password)
    db.commit()
    return True
