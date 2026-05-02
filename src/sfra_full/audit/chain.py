"""Tamper-evident hash chain for AuditEvent rows.

Each row stores:
    prev_hash    = current_hash of the previous row (NULL for the genesis row)
    current_hash = sha256(prev_hash || canonical_json(content))

``content`` is a deterministically-ordered subset of the row's fields:
``id, action, actor_id, actor_email, actor_role, target_kind, target_id,
request_method, request_path, response_status, detail, occurred_at``.

The recorder computes the hash inside the same DB transaction that
persists the row, holding a SELECT…FOR UPDATE on the previous row's id
to serialize concurrent writers. SQLite ignores the lock hint but
serializes via its global write lock anyway.

Verifying the chain after the fact recomputes every hash from genesis
and compares — see ``verify_chain``.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditEvent


_HASH_FIELDS = (
    "id",
    "action",
    "actor_id",
    "actor_email",
    "actor_role",
    "target_kind",
    "target_id",
    "request_method",
    "request_path",
    "response_status",
    "detail",
    "occurred_at",
)


def _canonical_payload(event: AuditEvent) -> bytes:
    """Deterministic JSON representation of the auditable fields.

    Datetimes are normalised to UTC ISO-8601 with a Z suffix so the hash
    stays stable across the SQLite roundtrip (which strips tzinfo) and
    Postgres (which preserves it).
    """
    from datetime import timezone

    payload: dict[str, Any] = {}
    for k in _HASH_FIELDS:
        v = getattr(event, k)
        if isinstance(v, datetime):
            if v.tzinfo is None:
                # Stored datetimes coming back from SQLite are naive UTC.
                v = v.replace(tzinfo=timezone.utc)
            else:
                v = v.astimezone(timezone.utc)
            # Microseconds preserved; drop "+00:00" → "Z" for canonical form.
            v = v.isoformat().replace("+00:00", "Z")
        elif hasattr(v, "value"):  # enum
            v = v.value
        payload[k] = v
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_hash(event: AuditEvent, prev_hash: Optional[str]) -> str:
    """sha256(prev_hash || canonical_payload)."""
    h = hashlib.sha256()
    h.update((prev_hash or "").encode("utf-8"))
    h.update(b"|")
    h.update(_canonical_payload(event))
    return h.hexdigest()


def latest_hash(session: Session) -> Optional[str]:
    """Return the most recent row's current_hash, or None if the table is empty."""
    return session.scalar(
        select(AuditEvent.current_hash)
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(1)
    )


def link_event(session: Session, event: AuditEvent) -> None:
    """Set ``event.prev_hash`` and ``event.current_hash`` immediately
    before the row is committed. Caller is responsible for the commit."""
    event.prev_hash = latest_hash(session)
    event.current_hash = compute_hash(event, event.prev_hash)


def verify_chain(session: Session) -> tuple[bool, Optional[str]]:
    """Recompute every row's hash and compare to the stored value.

    Returns ``(ok, first_bad_id)``. ``ok=True`` and ``first_bad_id=None``
    when the entire chain verifies. Otherwise ``ok=False`` and
    ``first_bad_id`` is the id of the earliest tampered/missing row.
    """
    rows = list(
        session.scalars(
            select(AuditEvent).order_by(AuditEvent.occurred_at.asc(), AuditEvent.id.asc())
        )
    )
    prev: Optional[str] = None
    for row in rows:
        if row.prev_hash != prev:
            return False, row.id
        expected = compute_hash(row, prev)
        if row.current_hash != expected:
            return False, row.id
        prev = row.current_hash
    return True, None


__all__ = ["compute_hash", "latest_hash", "link_event", "verify_chain"]
