"""Filesystem trace blob storage — spec v2 §2.

Layout:

    storage/
      <transformer_serial>/
        <overhaul_cycle_no>/
          <combination_code>/
            <role>/
              <sha256[:8]>_<filename>

This keeps a forensic copy of the raw uploaded file in addition to the
parsed numpy arrays in the DB (spec v2 §3 ``Trace.source_file_path``
field). The SHA-256 of the raw bytes is stored on the Trace row so we
can detect tampering / re-uploads.

Pluggable: the same interface is implemented later by an S3 backend
(``storage/s3.py``) and selected via ``SFRA_STORAGE_BACKEND``.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def _safe(name: str) -> str:
    """Filesystem-safe slug for a path segment."""
    name = (name or "").strip().replace(" ", "_")
    return _SAFE_CHARS.sub("_", name) or "_"


@dataclass(slots=True, frozen=True)
class StoredBlob:
    """Pointer to a persisted raw upload."""

    absolute_path: Path
    relative_path: Path  # relative to the storage root
    sha256: str
    bytes_written: int


class FilesystemStorage:
    """Filesystem-backed blob store. Idempotent on identical content."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        *,
        transformer_serial: str,
        overhaul_cycle_no: int,
        combination_code: Optional[str],
        role: str,
        original_filename: str,
        content: bytes,
    ) -> StoredBlob:
        """Persist ``content`` under the spec v2 layout.

        Re-uploads of the same bytes are no-ops (idempotent on SHA-256).
        Different bytes for an existing target name produce a new file
        keyed by SHA-256 prefix; the old file is preserved.
        """
        digest = sha256_hex(content)
        rel_dir = Path(
            _safe(transformer_serial),
            f"cycle_{int(overhaul_cycle_no):03d}",
            _safe(combination_code or "_unmapped"),
            _safe(role).lower(),
        )
        abs_dir = self.root / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)

        fname = f"{digest[:8]}_{_safe(original_filename or 'upload.bin')}"
        rel_path = rel_dir / fname
        abs_path = abs_dir / fname

        if not abs_path.exists():
            tmp = abs_path.with_suffix(abs_path.suffix + ".tmp")
            tmp.write_bytes(content)
            os.replace(tmp, abs_path)

        return StoredBlob(
            absolute_path=abs_path,
            relative_path=rel_path,
            sha256=digest,
            bytes_written=len(content),
        )

    def read(self, relative_path: Path | str) -> bytes:
        return (self.root / relative_path).read_bytes()

    def exists(self, relative_path: Path | str) -> bool:
        return (self.root / relative_path).exists()

    def delete(self, relative_path: Path | str) -> bool:
        target = self.root / relative_path
        if target.exists():
            target.unlink()
            return True
        return False

    def wipe(self) -> None:
        """DESTRUCTIVE — used by tests only via the dedicated fixture."""
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)


__all__ = ["FilesystemStorage", "StoredBlob", "sha256_hex"]
