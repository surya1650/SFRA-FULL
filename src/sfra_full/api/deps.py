"""FastAPI dependencies — DB session + storage backend.

State is stored on ``app.state`` by ``create_app`` so tests can inject
a custom engine and a tmp_path-based filesystem without monkeypatching.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from sfra_full.storage import FilesystemStorage


def get_session(request: Request) -> Generator[Session, None, None]:
    sm = request.app.state.sessionmaker
    with sm() as session:
        try:
            yield session
        finally:
            session.close()


def get_storage(request: Request) -> FilesystemStorage:
    return request.app.state.storage


def get_storage_root(request: Request) -> Path:
    return request.app.state.storage.root


__all__ = ["Depends", "get_session", "get_storage", "get_storage_root"]
