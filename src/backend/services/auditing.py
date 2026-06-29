from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from models.audit_log import AuditLog


def record(
    db: DBSession,
    *,
    action: str,
    target_type: str,
    target_id: str,
    user_id: UUID,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    """Write one audit_log entry in the caller's DB session.

    Called by every service that mutates data. The entry is committed with
    the surrounding operation — never separately.
    """
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    ))
    db.flush()
