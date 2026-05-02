"""User table + Role enum.

Adds the only new ORM model in Phase 2.3. Imported lazily by the auth
module so existing analysis code paths don't pull in passlib unless they
need to.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from sfra_full.db.base import Base


class Role(str, enum.Enum):
    """Spec v2 §2 role flags. Roles are additive — admin includes everything."""

    ENGINEER = "ENGINEER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(160))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SQLEnum(Role, name="user_role", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=Role.ENGINEER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


__all__ = ["Role", "User"]
