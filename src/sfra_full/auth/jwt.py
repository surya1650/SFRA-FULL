"""JWT issue + verify.

Uses python-jose to mint and parse HS256 access tokens. Secret is read
from ``SFRA_JWT_SECRET`` at runtime; tests can pass an explicit secret.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt


_DEFAULT_ALGORITHM = "HS256"
_DEFAULT_EXPIRY_MIN = 60 * 12  # 12 hours


class TokenError(Exception):
    """Raised when a JWT can't be issued or verified."""


def _secret(override: Optional[str] = None) -> str:
    secret = override or os.environ.get("SFRA_JWT_SECRET")
    if not secret:
        # MVP-safe sentinel: production deploys MUST set the env var.
        # The CLI's ``serve`` command refuses to start without it.
        secret = "DEV-ONLY-NEVER-USE-IN-PROD"
    return secret


def create_access_token(
    *,
    subject: str,
    role: str,
    expires_minutes: int = _DEFAULT_EXPIRY_MIN,
    secret: Optional[str] = None,
) -> str:
    """Mint an HS256 JWT carrying ``sub`` + ``role`` claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, _secret(secret), algorithm=_DEFAULT_ALGORITHM)


def decode_access_token(token: str, *, secret: Optional[str] = None) -> dict:
    """Verify + decode a JWT. Raises ``TokenError`` on any failure."""
    try:
        return jwt.decode(token, _secret(secret), algorithms=[_DEFAULT_ALGORITHM])
    except JWTError as exc:
        raise TokenError(str(exc)) from exc


__all__ = ["TokenError", "create_access_token", "decode_access_token"]
