"""Audit recorder — synchronous helper for route handlers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from .chain import compute_hash, latest_hash
from .models import AuditAction, AuditEvent


def record_event(
    session: Session,
    *,
    action: AuditAction,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    actor_role: Optional[str] = None,
    target_kind: Optional[str] = None,
    target_id: Optional[str] = None,
    request_method: Optional[str] = None,
    request_path: Optional[str] = None,
    response_status: Optional[int] = None,
    detail: Optional[dict[str, Any]] = None,
    commit: bool = False,
) -> AuditEvent:
    """Persist one audit event.

    By default leaves the commit to the calling transaction so the audit
    row writes atomically with the action it describes (e.g.
    UPLOAD_TESTED + the Trace insert). Pass ``commit=True`` for
    standalone events (LOGIN_FAILED, REPORT_GENERATE).
    """
    # Resolve the previous hash BEFORE the new row exists in the session,
    # otherwise SQLAlchemy's autoflush/identity map makes the un-hashed
    # new row visible to ``latest_hash`` and we'd chain off our own (None)
    # current_hash.
    prev = latest_hash(session)

    # Assign id and occurred_at explicitly so compute_hash sees the same
    # values the verifier will see after the row roundtrips through the DB.
    # SQLAlchemy column defaults run at INSERT time, but the hash must be
    # computed against the FINAL row state.
    ev = AuditEvent(
        id=uuid.uuid4().hex,
        action=action,
        actor_id=actor_id,
        actor_email=actor_email,
        actor_role=actor_role,
        target_kind=target_kind,
        target_id=target_id,
        request_method=request_method,
        request_path=request_path,
        response_status=response_status,
        detail=dict(detail) if detail else None,
        # Microsecond precision keeps `latest_hash` ordering stable when two
        # events race within the same second.
        occurred_at=datetime.now(timezone.utc),
    )
    ev.prev_hash = prev
    ev.current_hash = compute_hash(ev, prev)
    session.add(ev)
    if commit:
        session.commit()
    return ev


__all__ = ["record_event"]
