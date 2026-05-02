"""Audit recorder — synchronous helper for route handlers."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

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
    ev = AuditEvent(
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
    )
    session.add(ev)
    if commit:
        session.commit()
    return ev


__all__ = ["record_event"]
