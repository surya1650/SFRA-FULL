"""Structured audit log — spec v2 §11 + DL/T 911 evidentiary trail.

A append-only log of every engineer action with enough context to
reconstruct who-did-what-when from the DB alone. Used by:
- The reviewer console to verify reports were produced from un-tampered
  inputs.
- APTRANSCO compliance audits.
- Forensic investigation when a verdict is disputed.

Schema is intentionally narrow — actor / action / target / payload —
so it compresses well and queries cheaply.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum as SQLEnum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from sfra_full.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return uuid.uuid4().hex


class AuditAction(str, enum.Enum):
    """Closed set of audit-worthy actions. Add new values via Alembic migration."""

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"

    TRANSFORMER_CREATE = "TRANSFORMER_CREATE"
    TRANSFORMER_UPDATE = "TRANSFORMER_UPDATE"

    CYCLE_OPEN = "CYCLE_OPEN"
    CYCLE_CLOSE = "CYCLE_CLOSE"

    SESSION_CREATE = "SESSION_CREATE"

    UPLOAD_REFERENCE = "UPLOAD_REFERENCE"
    UPLOAD_TESTED = "UPLOAD_TESTED"
    UPLOAD_REPLACED = "UPLOAD_REPLACED"

    ANALYSIS_RUN = "ANALYSIS_RUN"
    ANALYSIS_REVIEW = "ANALYSIS_REVIEW"

    REPORT_GENERATE_PDF = "REPORT_GENERATE_PDF"
    REPORT_GENERATE_XLSX = "REPORT_GENERATE_XLSX"

    THRESHOLDS_UPDATE = "THRESHOLDS_UPDATE"

    USER_CREATE = "USER_CREATE"
    USER_DEACTIVATE = "USER_DEACTIVATE"


class AuditEvent(Base):
    """One immutable audit row with a tamper-evident hash chain.

    Each row stores ``current_hash = sha256(prev_hash || canonical(content))``.
    Verifying the chain (see ``audit.chain.verify_chain``) detects any
    UPDATE / DELETE / row-reorder even by an attacker with full DB
    write access — the only way to produce a clean chain after tampering
    is to recompute every hash from the tampered point forward, which
    is detectable as a chain divergence vs an off-host backup of any
    single row.
    """

    __tablename__ = "audit_event"
    __table_args__ = (
        Index("ix_audit_actor_time", "actor_id", "occurred_at"),
        Index("ix_audit_action_time", "action", "occurred_at"),
        Index("ix_audit_target", "target_kind", "target_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)

    actor_id: Mapped[Optional[str]] = mapped_column(String(32))
    actor_email: Mapped[Optional[str]] = mapped_column(String(255))
    actor_role: Mapped[Optional[str]] = mapped_column(String(16))

    action: Mapped[AuditAction] = mapped_column(
        SQLEnum(
            AuditAction,
            name="audit_action",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    target_kind: Mapped[Optional[str]] = mapped_column(String(32))
    target_id: Mapped[Optional[str]] = mapped_column(String(64))

    request_method: Mapped[Optional[str]] = mapped_column(String(8))
    request_path: Mapped[Optional[str]] = mapped_column(String(512))
    response_status: Mapped[Optional[int]] = mapped_column()

    detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Tamper-evident chain (Phase 5).
    prev_hash: Mapped[Optional[str]] = mapped_column(String(64))
    current_hash: Mapped[Optional[str]] = mapped_column(String(64))


__all__ = ["AuditAction", "AuditEvent"]
