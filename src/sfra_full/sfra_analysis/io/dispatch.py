"""Format detection and dispatch for SFRA file uploads.

Spec v2 §4 ``dispatch.py``: detect format from extension + magic bytes,
then call the right parser. Returns ``(format, list[ParsedSweep])`` so
the caller can record what was parsed and warn the engineer if a format
fell back to the generic path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .base import ParsedSweep
from .csv import parse_csv
from .doble import parse_doble
from .frax import parse_frax
from .omicron import parse_omicron


def parse_file(
    source: Union[str, bytes, Path],
    *,
    source_filename: Optional[str] = None,
) -> tuple[str, list[ParsedSweep]]:
    """Detect format and parse. Returns ``(format_name, sweeps)``.

    Detection order:
        1. .frax extension OR XML markers (<Frameworx, <frax, <Sweep)
        2. .csv / .tsv extension OR comma-delimited content
        3. .xfra (Doble) — handled via generic CSV/header path for now
        4. .xml / .fra / .sfra — also handled via FRAX parser (permissive)
    """
    if isinstance(source, (str, Path)) and Path(str(source)).exists():
        path = Path(source)
        ext = path.suffix.lower()
        head = path.read_bytes()[:4096]
        filename = source_filename or path.name
        bytes_payload: bytes = path.read_bytes()
    elif isinstance(source, bytes):
        bytes_payload = source
        head = source[:4096]
        filename = source_filename or ""
        ext = Path(filename).suffix.lower()
    else:
        text = str(source)
        bytes_payload = text.encode("utf-8")
        head = bytes_payload[:4096]
        filename = source_filename or ""
        ext = Path(filename).suffix.lower()

    head_lower = head.lower()

    # OMICRON FRAnalyzer — INI-style sections.
    if b"[header]" in head_lower or b"[data]" in head_lower:
        try:
            sweeps = parse_omicron(bytes_payload, source_filename=filename)
        except Exception:
            sweeps = []
        if sweeps:
            return "OMICRON", sweeps

    # MEGGER FRAX (real schema) or legacy FRAXFile / Measurement form.
    if (
        ext in {".frax", ".xml", ".fra", ".sfra"}
        or b"<frameworx" in head_lower
        or b"<frax" in head_lower
        or b"<sweep" in head_lower
        or b"<measurement" in head_lower
    ):
        sweeps = parse_frax(bytes_payload, source_filename=filename)
        if sweeps:
            return "FRAX", sweeps

    # Doble M5400 / M5300 — .xfra extension or "Test Date:" header marker.
    if ext == ".xfra" or b"test date:" in head_lower or b"transformer:" in head_lower[:512]:
        try:
            sweeps = parse_doble(bytes_payload, source_filename=filename)
        except Exception:
            sweeps = []
        if sweeps:
            return "DOBLE", sweeps

    sweeps = parse_csv(bytes_payload, source_filename=filename)
    return "CSV", sweeps


__all__ = ["parse_file"]
