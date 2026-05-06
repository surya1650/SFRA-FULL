"""FastAPI application factory."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sfra_full import __version__
from sfra_full.db import Base, build_engine, build_sessionmaker, resolve_database_url
from sfra_full.storage import FilesystemStorage

from .routes import (
    analyses,
    audit,
    auth,
    health,
    reports,
    sessions,
    standards,
    traces,
    transformers,
)
from sfra_full.audit.models import AuditEvent  # noqa: F401 — register on metadata
from sfra_full.auth.models import User  # noqa: F401 — register on metadata


def create_app(
    *,
    database_url: Optional[str] = None,
    storage_root: Optional[Path | str] = None,
    create_schema: bool = False,
) -> FastAPI:
    """Build a FastAPI app with the configured engine + storage.

    Args:
        database_url: override SFRA_DATABASE_URL (test fixtures use ``sqlite://``).
        storage_root: directory for raw uploaded blobs; defaults to ``data/storage``.
        create_schema: when True, run ``Base.metadata.create_all`` at startup.
            Tests pass True; production uses Alembic migrations and leaves it False.
    """
    app = FastAPI(
        title="APTRANSCO SFRA Diagnostic Tool",
        description=(
            "Sweep Frequency Response Analysis platform — IEEE C57.149-2012 / "
            "IEC 60076-18 / DL/T 911-2004 / CIGRE TB 342."
        ),
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = build_engine(database_url or resolve_database_url())
    if create_schema:
        Base.metadata.create_all(engine)

    if storage_root is None:
        repo_root = Path(__file__).resolve().parents[3]
        storage_root = repo_root / "data" / "storage"
    storage = FilesystemStorage(storage_root)

    app.state.engine = engine
    app.state.sessionmaker = build_sessionmaker(engine)
    app.state.storage = storage

    app.include_router(health.router)
    app.include_router(standards.router)
    app.include_router(transformers.router)
    app.include_router(sessions.router)
    app.include_router(traces.router)
    app.include_router(analyses.router)
    app.include_router(reports.router)
    app.include_router(auth.router)
    app.include_router(audit.router)
    # SSO IdP integration intentionally deferred — see docs/DECISIONS.md
    # entry "2026-05-02 · SSO router removed". The auth/sso.py module
    # still exists but is not wired into the app.

    return app


app = create_app()


__all__ = ["app", "create_app"]
