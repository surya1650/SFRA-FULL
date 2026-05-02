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
from sfra_full.audit import AuditAction, AuditEvent, verify_chain
from sfra_full.auth import require_admin, require_reviewer


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
    prev_hash: Optional[str]
    current_hash: Optional[str]


class ChainVerifyResponse(BaseModel):
    ok: bool
    first_bad_id: Optional[str]
    n_rows: int


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


@router.get(
    "/verify",
    response_model=ChainVerifyResponse,
    dependencies=[Depends(require_admin)],
)
def verify_audit_chain(session: Session = Depends(get_session)) -> ChainVerifyResponse:
    """Recompute and verify the tamper-evident audit hash chain.

    Returns ``ok=true`` on a clean chain, otherwise ``first_bad_id`` is
    the earliest divergence — points to the tampered/missing/reordered
    row. Counts every row included in the verification (including the
    bad one if any) for operator context.
    """
    from sqlalchemy import func
    from sfra_full.audit.models import AuditEvent as _AE
    n = int(session.scalar(select(func.count()).select_from(_AE)) or 0)
    ok, bad = verify_chain(session)
    return ChainVerifyResponse(ok=ok, first_bad_id=bad, n_rows=n)
