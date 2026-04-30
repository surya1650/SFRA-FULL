"""Filesystem storage tests — SHA-256 keying, idempotency, layout."""
from __future__ import annotations

from sfra_full.storage import FilesystemStorage, sha256_hex


def test_sha256_is_deterministic():
    a = sha256_hex(b"hello world")
    b = sha256_hex(b"hello world")
    assert a == b
    assert len(a) == 64


def test_store_creates_layout(tmp_path):
    fs = FilesystemStorage(tmp_path / "store")
    blob = fs.store(
        transformer_serial="TR-A1",
        overhaul_cycle_no=1,
        combination_code="EEOC_HV_R",
        role="REFERENCE",
        original_filename="ref.frax",
        content=b"<FRAXFile/>",
    )
    assert blob.absolute_path.exists()
    parts = blob.relative_path.parts
    assert parts[0] == "TR-A1"
    assert parts[1] == "cycle_001"
    assert parts[2] == "EEOC_HV_R"
    assert parts[3] == "reference"
    assert parts[4].startswith(blob.sha256[:8])
    assert blob.sha256 == sha256_hex(b"<FRAXFile/>")


def test_idempotent_on_identical_content(tmp_path):
    fs = FilesystemStorage(tmp_path / "store")
    a = fs.store(
        transformer_serial="X", overhaul_cycle_no=1, combination_code="EEOC_HV_R",
        role="TESTED", original_filename="x.csv", content=b"f,m\n100,-20",
    )
    b = fs.store(
        transformer_serial="X", overhaul_cycle_no=1, combination_code="EEOC_HV_R",
        role="TESTED", original_filename="x.csv", content=b"f,m\n100,-20",
    )
    assert a.absolute_path == b.absolute_path
    assert a.sha256 == b.sha256


def test_unmapped_combination_routed_to_underscore(tmp_path):
    fs = FilesystemStorage(tmp_path / "store")
    blob = fs.store(
        transformer_serial="X", overhaul_cycle_no=1, combination_code=None,
        role="TESTED", original_filename="x.frax", content=b"<x/>",
    )
    assert "_unmapped" in blob.relative_path.parts


def test_unsafe_filename_sanitized(tmp_path):
    fs = FilesystemStorage(tmp_path / "store")
    blob = fs.store(
        transformer_serial="../etc/passwd", overhaul_cycle_no=1,
        combination_code="EEOC_HV_R", role="TESTED",
        original_filename="evil ../path.csv", content=b"data",
    )
    # Stored within root, never outside.
    assert (tmp_path / "store") in blob.absolute_path.parents
