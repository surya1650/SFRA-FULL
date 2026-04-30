"""Generic CSV / TSV parser — spec v2 §4.2.

Behaviour:
    - Auto-detect delimiter: comma, semicolon, or tab.
    - Auto-detect Hz vs kHz (if max < 1e5, treat as kHz; else Hz).
    - Auto-detect phase units: |phase|.max() > 2π → degrees, else radians.
    - Skip optional single-line header.
    - Always returns a list of length 1 (CSVs hold a single sweep).
"""
from __future__ import annotations

import csv as csvlib
import io
import math
from pathlib import Path
from typing import Optional, Union

import numpy as np

from .base import ParsedSweep


_DELIMS = (",", ";", "\t")


def parse_csv(
    source: Union[str, bytes, Path],
    *,
    source_filename: Optional[str] = None,
    label: Optional[str] = None,
) -> list[ParsedSweep]:
    """Parse a CSV/TSV file with auto-detected delimiter and units."""
    if isinstance(source, (str, Path)) and Path(str(source)).exists():
        path = Path(source)
        text = path.read_text(encoding="utf-8", errors="replace")
        filename = source_filename or path.name
    elif isinstance(source, bytes):
        text = source.decode("utf-8", errors="replace")
        filename = source_filename or ""
    else:
        text = str(source)
        filename = source_filename or ""

    delim = _detect_delim(text)
    rows = list(csvlib.reader(io.StringIO(text), delimiter=delim))
    if not rows:
        raise ValueError("CSV is empty")

    # Drop optional header row.
    if _looks_like_header(rows[0]):
        rows = rows[1:]

    f_list: list[float] = []
    m_list: list[float] = []
    p_list: list[float] = []
    have_phase = True

    for row in rows:
        cols = [c.strip() for c in row if c.strip()]
        if len(cols) < 2:
            continue
        try:
            f = float(cols[0])
            m = float(cols[1])
        except ValueError:
            continue
        f_list.append(f)
        m_list.append(m)
        if have_phase and len(cols) >= 3:
            try:
                p_list.append(float(cols[2]))
            except ValueError:
                have_phase = False
        else:
            have_phase = False

    if not f_list:
        raise ValueError("CSV contains no numeric data rows")

    f_arr = np.asarray(f_list, dtype=float)
    m_arr = np.asarray(m_list, dtype=float)

    # kHz auto-detect.
    if f_arr.max() < 1e5:
        f_arr = f_arr * 1000.0  # treat as kHz → Hz

    p_arr: Optional[np.ndarray] = None
    if have_phase and len(p_list) == len(f_list):
        p = np.asarray(p_list, dtype=float)
        # Radians vs degrees auto-detect.
        if np.max(np.abs(p)) <= 2.0 * math.pi + 0.5:
            p = p * 180.0 / math.pi
        p_arr = np.unwrap(np.deg2rad(p)) * 180.0 / math.pi

    return [
        ParsedSweep(
            label=label or filename or "csv-sweep",
            frequency_hz=f_arr,
            magnitude_db=m_arr,
            phase_deg=p_arr,
            properties={},
            source_format="CSV",
            source_file=filename,
        )
    ]


def _detect_delim(text: str) -> str:
    sample = text[:4096]
    counts = {d: sample.count(d) for d in _DELIMS}
    return max(counts, key=lambda k: counts[k])


def _looks_like_header(row: list[str]) -> bool:
    """Treat a row as a header if any cell is non-numeric."""
    if not row:
        return False
    for cell in row:
        c = cell.strip()
        if not c:
            continue
        try:
            float(c)
        except ValueError:
            return True
    return False


__all__ = ["parse_csv"]
