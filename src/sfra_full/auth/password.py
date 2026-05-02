"""Password hashing — bcrypt directly.

Originally used passlib but its bcrypt backend breaks with bcrypt>=4
(`bcrypt.__about__` removed). Calling the bcrypt module directly is
simpler and version-stable.
"""
from __future__ import annotations

import bcrypt


_BCRYPT_MAX_BYTES = 72  # bcrypt input is silently truncated above 72 bytes;
                       # we explicitly truncate to make the behaviour
                       # observable and consistent.


def _to_bytes(s: str) -> bytes:
    return s.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    if not isinstance(plain, str):
        raise TypeError("password must be a str")
    return bcrypt.hashpw(_to_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


__all__ = ["hash_password", "verify_password"]
