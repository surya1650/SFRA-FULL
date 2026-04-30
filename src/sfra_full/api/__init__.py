"""FastAPI application + routers — spec v2 §6 / §11.

Public exports:
    app          — the FastAPI application instance
    create_app   — factory for tests with a custom DB URL / storage root

Routes:
    GET  /api/health
    GET  /api/standards/combinations
    POST /api/transformers
    GET  /api/transformers
    GET  /api/transformers/{id}
    POST /api/transformers/{id}/cycles
    POST /api/transformers/{id}/sessions
    GET  /api/sessions/{id}
    POST /api/sessions/{id}/upload          (single-trace OR batch FRAX)
    POST /api/sessions/{id}/analyse         (run Mode 1/2 for any pending traces)
    GET  /api/traces/{id}
    GET  /api/analyses/{id}
"""
from __future__ import annotations

from .app import app, create_app

__all__ = ["app", "create_app"]
