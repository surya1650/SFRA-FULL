"""GET /api/health — liveness + version."""
from __future__ import annotations

from fastapi import APIRouter

from sfra_full import __version__

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
