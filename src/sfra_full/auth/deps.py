"""FastAPI dependencies for the auth subsystem."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from sfra_full.api.deps import get_session

from .jwt import TokenError, decode_access_token
from .models import Role, User


def _extract_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization header")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Authorization scheme must be Bearer"
        )
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    token = _extract_token(authorization)
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing subject")
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


_ROLE_RANK = {Role.ENGINEER: 1, Role.REVIEWER: 2, Role.ADMIN: 3}


def _require_role(min_role: Role):
    """Build a dependency that enforces ``user.role >= min_role``."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if _ROLE_RANK[user.role] < _ROLE_RANK[min_role]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requires {min_role.value} role; have {user.role.value}",
            )
        return user

    return dependency


require_engineer = _require_role(Role.ENGINEER)
require_reviewer = _require_role(Role.REVIEWER)
require_admin = _require_role(Role.ADMIN)


__all__ = [
    "get_current_user",
    "require_admin",
    "require_engineer",
    "require_reviewer",
]
