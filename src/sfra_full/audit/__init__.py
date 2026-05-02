"""Audit log subsystem.

Public surface:
    record_event(session, *, action, actor=None, target_kind=None, target_id=None, ...)
        Synchronous helper used by route handlers and middleware.

The audit log is **append-only** by convention — there's no UPDATE or
DELETE in the codebase. Operators may purge old rows directly via SQL
once retention policy is set, but the application never modifies a row
once written.
"""
from __future__ import annotations

from .models import AuditAction, AuditEvent
from .recorder import record_event

__all__ = ["AuditAction", "AuditEvent", "record_event"]
