"""Auth scaffold — JWT + Engineer/Reviewer/Admin roles + APTRANSCO SSO hook.

Phase 2 ships:
    - users table + bcrypt password hashing
    - JWT issue/verify
    - role enum (ENGINEER / REVIEWER / ADMIN)
    - FastAPI dependency for current user + role gates
    - ``auth.sso`` placeholder (returns a 501 endpoint until APTRANSCO
      identity provider details are confirmed)

Deliberately scoped to MVP: no refresh tokens, no password reset, no
audit log table yet. Those come in Phase 3 once the user model survives
contact with real users.
"""
from __future__ import annotations

from .jwt import create_access_token, decode_access_token
from .models import Role, User
from .password import hash_password, verify_password
from .deps import (
    get_current_user,
    require_admin,
    require_engineer,
    require_reviewer,
)

__all__ = [
    "Role",
    "User",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "hash_password",
    "require_admin",
    "require_engineer",
    "require_reviewer",
    "verify_password",
]
