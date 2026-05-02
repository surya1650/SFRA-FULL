"""GET /api/audit — admin-only audit log query.

Filterable by actor / action / target / time window. Returns the most
recent 200 events by default; pagination via ``before=<iso8601>``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfra_full.api.deps import get_session
from sfra_full.audit import AuditAction, AuditEvent
from sfra_full.auth import require_reviewer


router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_id: Optional[str]
    actor_email: Optional[str]
    actor_role: Optional[str]
    action: AuditAction
    target_kind: Optional[str]
    target_id: Optional[str]
    request_method: Optional[str]
    request_path: Optional[str]
    response_status: Optional[int]
    detail: Optional[dict[str, Any]]
    occurred_at: datetime


@router.get("", response_model=list[AuditEventOut], dependencies=[Depends(require_reviewer)])
def list_events(
    session: Session = Depends(get_session),
    actor_id: Optional[str] = None,
    action: Optional[AuditAction] = None,
    target_kind: Optional[str] = None,
    target_id: Optional[str] = None,
    before: Optional[datetime] = Query(None, description="Return events strictly before this UTC timestamp"),
    limit: int = Query(200, ge=1, le=1000),
) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if target_kind:
        stmt = stmt.where(AuditEvent.target_kind == target_kind)
    if target_id:
        stmt = stmt.where(AuditEvent.target_id == target_id)
    if before:
        stmt = stmt.where(AuditEvent.occurred_at < before)
    return list(session.scalars(stmt))
