"""Base dataclass shared by every SFRA parser.

Per spec v2 §4: every parser returns the same shape, regardless of source
format. A ``.frax`` parser returns ``list[ParsedSweep]`` with one entry per
embedded sweep; CSV/Doble/Generic parsers return a list of length 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np


@dataclass(slots=True)
class ParsedSweep:
    """One normalised SFRA sweep as emitted by any parser.

    Fields match spec v2 §4 ``ParsedSweep``:

    label                — human-readable label, e.g. "1u-1n [open, LTC=Max]"
    properties           — raw FRAX <Property> dict (or analogue from other formats)
    combination_code     — resolved spec v2 §5 code (e.g. "EEOC_HV_R") or None
    tap_current          — current OLTC tap position (str or int)
    tap_previous         — previous OLTC tap position
    detc_tap             — DETC (de-energised tap changer) tap position
    frequency_hz         — strictly increasing frequency array
    magnitude_db         — magnitude in dB (already converted from FRAX linear)
    phase_deg            — phase in degrees, unwrapped
    instrument_metadata  — instrument serial, calibration date, firmware versions
    raw_header           — verbatim header text (for forensic display)
    source_format        — 'FRAX' | 'CSV' | 'XFRA' | 'XML' | 'FRA' | 'SFRA'
    source_file          — original filename (for audit log + storage layout)
    """

    label: str
    frequency_hz: np.ndarray
    magnitude_db: np.ndarray
    phase_deg: Optional[np.ndarray] = None
    properties: dict[str, Any] = field(default_factory=dict)
    combination_code: Optional[str] = None
    tap_current: Optional[Any] = None
    tap_previous: Optional[Any] = None
    detc_tap: Optional[Any] = None
    instrument_metadata: dict[str, Any] = field(default_factory=dict)
    raw_header: str = ""
    source_format: str = "unknown"
    source_file: str = ""

    def __post_init__(self) -> None:
        self.frequency_hz = np.asarray(self.frequency_hz, dtype=float)
        self.magnitude_db = np.asarray(self.magnitude_db, dtype=float)
        if self.phase_deg is not None:
            self.phase_deg = np.asarray(self.phase_deg, dtype=float)
        if self.frequency_hz.shape != self.magnitude_db.shape:
            raise ValueError(
                f"Sweep '{self.label}' freq/mag length mismatch: "
                f"{self.frequency_hz.shape} vs {self.magnitude_db.shape}"
            )
        # Enforce strictly increasing frequency.
        if self.frequency_hz.size > 1 and np.any(np.diff(self.frequency_hz) <= 0):
            order = np.argsort(self.frequency_hz)
            self.frequency_hz = self.frequency_hz[order]
            self.magnitude_db = self.magnitude_db[order]
            if self.phase_deg is not None:
                self.phase_deg = self.phase_deg[order]


__all__ = ["ParsedSweep"]
