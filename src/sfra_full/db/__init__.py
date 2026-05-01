"""Database layer — SQLAlchemy 2.x async + Alembic.

Spec v2 §2-§3 layout:

    Engine: PostgreSQL 15+ in production, SQLite for local dev
            (selected via ``SFRA_DATABASE_URL`` env var).
    ORM:    SQLAlchemy 2.x with the typed declarative API.
    Migrations: Alembic, never hand-edit SQL.

Public surface:

    - ``Base``                   — DeclarativeBase
    - ``get_engine() / get_sessionmaker()``
    - ``Transformer / OverhaulCycle / TestSession / Combination / Trace / AnalysisResult``
"""
from __future__ import annotations

from .base import (
    Base,
    build_engine,
    build_sessionmaker,
    get_engine,
    get_sessionmaker,
    resolve_database_url,
)
from .enums import (
    AnalysisModeDB,
    InterventionType,
    SessionType,
    SeverityDB,
    SourceFormat,
    TraceRole,
    TransformerType,
)
from .models import (
    AnalysisResult,
    Combination,
    OverhaulCycle,
    TestSession,
    Trace,
    Transformer,
)

__all__ = [
    "AnalysisModeDB",
    "AnalysisResult",
    "Base",
    "Combination",
    "InterventionType",
    "OverhaulCycle",
    "SessionType",
    "SeverityDB",
    "SourceFormat",
    "TestSession",
    "Trace",
    "TraceRole",
    "Transformer",
    "TransformerType",
    "build_engine",
    "build_sessionmaker",
    "get_engine",
    "get_sessionmaker",
    "resolve_database_url",
]
