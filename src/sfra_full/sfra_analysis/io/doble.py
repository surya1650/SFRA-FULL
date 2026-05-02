"""Doble M5400 / M5300 (.xfra, .csv) parser.

Doble exports are tab-delimited text with a header block followed by a
data section. Header lines look like:

    Test Date: 2024-04-15
    Transformer: TR-A1
    Winding: HV
    Phase: A

then a blank line, then column headers, then numeric rows:

    Frequency Hz   Magnitude dB   Phase deg
    20             -23.45          -89.12
    ...

The parser is permissive — it accepts any whitespace-tabular layout where
the first numeric row marks the start of data, and falls back to comma /
semicolon delimiters if tabs aren't present.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Optional, Union

import numpy as np

from .base import ParsedSweep


_HEADER_KEYS = (
    "transformer", "winding", "phase", "tap", "test type", "test date",
    "instrument", "operator", "tested by", "temperature",
)


def parse_doble(
    source: Union[str, bytes, Path],
    *,
    source_filename: Optional[str] = None,
) -> list[ParsedSweep]:
    """Parse a Doble .xfra / .csv export."""
    text, filename = _decode(source, source_filename)

    header_meta: dict[str, str] = {}
    data_rows: list[list[str]] = []
    in_data = False

    delim = _detect_delim(text)
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if not in_data:
            # Try to interpret as a header "key: value" line.
            if ":" in line:
                k, _, v = line.partition(":")
                key = k.strip().lower()
                if key in _HEADER_KEYS:
                    header_meta[key] = v.strip()
                    continue
            # Detect when numeric rows start.
            cells = [c for c in re.split(r"[,\t;]\s*|\s{2,}", line) if c]
            if len(cells) >= 2 and _looks_numeric(cells[0]):
                in_data = True
                data_rows.append(cells)
                continue
            # Header continuation that doesn't match — skip.
            continue
        cells = [c for c in re.split(r"[,\t;]\s*|\s{2,}", line) if c]
        if cells:
            data_rows.append(cells)

    # Fallback path: try the csv module with the detected delimiter.
    if not data_rows:
        reader = csv.reader(io.StringIO(text), delimiter=delim)
        for cells in reader:
            cells = [c.strip() for c in cells if c.strip()]
            if len(cells) >= 2 and _looks_numeric(cells[0]):
                data_rows.append(cells)

    if not data_rows:
        raise ValueError("No numeric data rows found in Doble file")

    freqs: list[float] = []
    mags: list[float] = []
    phases: list[float] = []
    have_phase = True
    for row in data_rows:
        try:
            f = float(row[0])
            m = float(row[1])
        except (ValueError, IndexError):
            continue
        freqs.append(f)
        mags.append(m)
        if have_phase and len(row) >= 3:
            try:
                phases.append(float(row[2]))
            except ValueError:
                have_phase = False
        else:
            have_phase = False

    f_arr = np.asarray(freqs, dtype=float)
    m_arr = np.asarray(mags, dtype=float)
    p_arr: Optional[np.ndarray] = None
    if have_phase and len(phases) == len(freqs):
        p = np.asarray(phases, dtype=float)
        # Heuristic: if max |phase| < 2π+0.5, assume radians.
        if np.max(np.abs(p)) < 7.0:
            p = np.rad2deg(p)
        p_arr = np.unwrap(np.deg2rad(p)) * 180.0 / np.pi

    label = (
        header_meta.get("transformer", "")
        + (
            f" / {header_meta['winding']}"
            if header_meta.get("winding")
            else ""
        )
        + (f" / phase {header_meta['phase']}" if header_meta.get("phase") else "")
    ).strip(" /") or "doble-sweep"

    return [
        ParsedSweep(
            label=label,
            frequency_hz=f_arr,
            magnitude_db=m_arr,
            phase_deg=p_arr,
            properties=dict(header_meta),
            tap_current=header_meta.get("tap"),
            source_format="XFRA",
            source_file=filename,
        )
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _decode(
    source: Union[str, bytes, Path], filename: Optional[str]
) -> tuple[str, str]:
    if isinstance(source, (str, Path)) and Path(str(source)).exists():
        path = Path(source)
        return path.read_text(encoding="utf-8", errors="replace"), filename or path.name
    if isinstance(source, bytes):
        return source.decode("utf-8", errors="replace"), filename or ""
    return str(source), filename or ""


def _detect_delim(text: str) -> str:
    sample = text[:4096]
    counts = {d: sample.count(d) for d in ("\t", ",", ";")}
    return max(counts, key=lambda k: counts[k]) or "\t"


_NUM_RE = re.compile(r"^[+\-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+\-]?\d+)?$")


def _looks_numeric(s: str) -> bool:
    return bool(_NUM_RE.match(s.strip()))


__all__ = ["parse_doble"]
