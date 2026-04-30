"""Storage layer — filesystem-backed (default) or S3-backed (later).

Phase 1 ships only the filesystem implementation. The S3 backend will
implement the same interface in Phase 2 / 3 and is selected via the
``SFRA_STORAGE_BACKEND`` environment variable.
"""
from __future__ import annotations

from .filesystem import FilesystemStorage, StoredBlob, sha256_hex

__all__ = ["FilesystemStorage", "StoredBlob", "sha256_hex"]
