"""Engine, sessionmaker, declarative base.

Selects between SQLite (default, dev) and PostgreSQL (production) based
on ``SFRA_DATABASE_URL``. Both are supported by SQLAlchemy 2.x with the
same declarative API; only the URL changes:

    sqlite:///data/app.db                                  (dev default)
    postgresql+psycopg://user:pwd@host:5432/sfra           (prod)

Phase 1 is sync-only. The async engine + AsyncSession hook lands in
Phase 2 once we need WebSocket / SSE for live re-analysis.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# Use a deterministic naming convention so Alembic autogenerate stays stable
# across SQLite / Postgres backends.
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Project-wide declarative base."""

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


def _default_sqlite_url() -> str:
    """Default to a file-based SQLite under ``data/`` so dev runs need no setup."""
    repo = Path(__file__).resolve().parents[3]
    db_dir = repo / "data"
    db_dir.mkdir(exist_ok=True)
    return f"sqlite:///{db_dir / 'app.db'}"


def resolve_database_url(override: Optional[str] = None) -> str:
    if override:
        return override
    return os.environ.get("SFRA_DATABASE_URL") or _default_sqlite_url()


def build_engine(url: Optional[str] = None, *, echo: bool = False) -> Engine:
    """Construct a fresh SQLAlchemy Engine. Tests use this with in-memory SQLite."""
    db_url = resolve_database_url(url)
    connect_args: dict = {}
    if db_url.startswith("sqlite"):
        # Allow cross-thread access for the FastAPI test client; SQLite-only.
        connect_args["check_same_thread"] = False
    return create_engine(db_url, echo=echo, future=True, connect_args=connect_args)


def build_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


# Module-level cached engine for the default URL — convenient for the CLI
# and the FastAPI dependency. Tests override via build_engine() directly.
@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return build_engine()


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return build_sessionmaker(get_engine())


def reset_engine_cache() -> None:
    """Drop the cached engine — useful for tests that want a fresh URL."""
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


__all__ = [
    "Base",
    "build_engine",
    "build_sessionmaker",
    "get_engine",
    "get_sessionmaker",
    "reset_engine_cache",
    "resolve_database_url",
]
