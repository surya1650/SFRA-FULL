"""OMICRON FRAnalyzer (.fra, .csv) parser.

OMICRON exports use an INI-style section header:

    [Header]
    Transformer=TR-A1
    Winding=HV
    Phase=A
    Test=End-to-end
    OpenShort=Open
    Tap=5
    Date=2024-04-15

    [Data]
    Frequency,Magnitude,Phase
    20.0,-23.45,-89.12
    ...

The parser handles both the section-headered form and a permissive
fallback where the file is plain CSV with a column header line.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Optional, Union

import numpy as np

from .base import ParsedSweep
from .combination_resolver import resolve_combination_code


_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")


def parse_omicron(
    source: Union[str, bytes, Path],
    *,
    source_filename: Optional[str] = None,
) -> list[ParsedSweep]:
    """Parse an OMICRON FRAnalyzer export."""
    text, filename = _decode(source, source_filename)

    sections: dict[str, list[str]] = {}
    current: Optional[str] = None
    for raw in text.splitlines():
        m = _SECTION_RE.match(raw)
        if m:
            current = m.group(1).strip().lower()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(raw)

    header_meta: dict[str, str] = {}
    if "header" in sections:
        for line in sections["header"]:
            if "=" in line:
                k, _, v = line.partition("=")
                header_meta[k.strip().lower()] = v.strip()

    if "data" in sections:
        body = "\n".join(sections["data"])
    else:
        # No section markers — assume the whole file is CSV-shaped.
        body = text

    data_lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if not data_lines:
        raise ValueError("OMICRON file has no [Data] section")

    delim = _detect_delim(body)
    reader = csv.reader(io.StringIO("\n".join(data_lines)), delimiter=delim)
    rows = list(reader)
    if rows and not _looks_numeric(rows[0][0] if rows[0] else ""):
        rows = rows[1:]

    freqs: list[float] = []
    mags: list[float] = []
    phases: list[float] = []
    have_phase = True
    for cells in rows:
        cells = [c.strip() for c in cells if c.strip()]
        if len(cells) < 2:
            continue
        try:
            f = float(cells[0])
            m = float(cells[1])
        except ValueError:
            continue
        freqs.append(f)
        mags.append(m)
        if have_phase and len(cells) >= 3:
            try:
                phases.append(float(cells[2]))
            except ValueError:
                have_phase = False
        else:
            have_phase = False

    if not freqs:
        raise ValueError("OMICRON file: no numeric rows in [Data]")

    f_arr = np.asarray(freqs, dtype=float)
    m_arr = np.asarray(mags, dtype=float)
    p_arr: Optional[np.ndarray] = None
    if have_phase and len(phases) == len(freqs):
        p_arr = np.unwrap(np.deg2rad(np.asarray(phases, dtype=float))) * 180.0 / np.pi

    # Normalise header keys to the FRAX <Property name> casing the
    # combination resolver expects.
    properties = {
        "Test": header_meta.get("test"),
        "OpenShort": header_meta.get("openshort") or header_meta.get("open/short"),
        "Phase": header_meta.get("phase"),
        "Winding": header_meta.get("winding"),
        "Tap": header_meta.get("tap"),
        "Shorted terminals": header_meta.get("shorted terminals") or header_meta.get("shorted"),
    }
    properties = {k: v for k, v in properties.items() if v}
    code = resolve_combination_code(properties) if properties else None

    return [
        ParsedSweep(
            label=header_meta.get("transformer", "omicron-sweep"),
            frequency_hz=f_arr,
            magnitude_db=m_arr,
            phase_deg=p_arr,
            properties={**header_meta, **properties},
            combination_code=code,
            tap_current=header_meta.get("tap"),
            source_format="FRA",
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
    counts = {d: sample.count(d) for d in (",", ";", "\t")}
    return max(counts, key=lambda k: counts[k]) or ","


_NUM_RE = re.compile(r"^[+\-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+\-]?\d+)?$")


def _looks_numeric(s: str) -> bool:
    return bool(_NUM_RE.match(s.strip()))


__all__ = ["parse_omicron"]
