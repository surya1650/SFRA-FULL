"""Frequency-band definitions — single source of truth for analysis.

Loaded from ``standards/ieee_c57_149_combinations.yaml`` so the catalogue
file remains the only place band boundaries are written. Edit the YAML;
tests catch any drift.

Two band sets are kept side-by-side:

- ``BANDS_SPEC_V2``  — IEEE C57.149 / spec v2 §7.2 (LOW / MID_L / MID / HIGH)
                      used for comparative metrics, plotting, and verdicts.
- ``DL_T_911_BANDS`` — DL/T 911-2004 (RLW / RLM / RLH) used only for the
                      RL-factor diagnostic in ``statistical.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import yaml


CATALOGUE_PATH = (
    Path(__file__).resolve().parents[3]
    / "standards"
    / "ieee_c57_149_combinations.yaml"
)


@dataclass(frozen=True, slots=True)
class BandSpec:
    """One named frequency band."""

    code: str
    min_hz: float
    max_hz: float
    dominates: str = ""

    def mask(self, frequency_hz: np.ndarray) -> np.ndarray:
        """Boolean mask selecting samples within this band (inclusive)."""
        return (frequency_hz >= self.min_hz) & (frequency_hz <= self.max_hz)

    def slice(
        self, frequency_hz: np.ndarray, *arrays: np.ndarray
    ) -> tuple[np.ndarray, ...]:
        """Return ``(f, *arrays)`` filtered to this band.

        Useful for per-band metrics — pass any number of co-indexed arrays.
        """
        m = self.mask(frequency_hz)
        return (frequency_hz[m],) + tuple(a[m] for a in arrays)


# ---------------------------------------------------------------------------
# YAML loader (cached)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_bands_yaml() -> dict[str, list[dict]]:
    with CATALOGUE_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data.get("bands", {})


def _build_band_set(yaml_key: str, *, drop_optional: bool = True) -> list[BandSpec]:
    raw = _load_bands_yaml().get(yaml_key, [])
    out: list[BandSpec] = []
    for entry in raw:
        if drop_optional and entry.get("optional"):
            continue
        out.append(
            BandSpec(
                code=entry["code"],
                min_hz=float(entry["min_hz"]),
                max_hz=float(entry["max_hz"]),
                dominates=entry.get("dominates", ""),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Public band sets — module-level constants
# ---------------------------------------------------------------------------
BANDS_SPEC_V2: list[BandSpec] = _build_band_set("spec_v2")
"""Spec v2 §7.2 bands: LOW / MID_L / MID / HIGH (HIGH_EXT optional, dropped)."""

DL_T_911_BANDS: list[BandSpec] = _build_band_set("dl_t_911")
"""DL/T 911-2004 bands: RLW / RLM / RLH used for the relative factor diagnostic."""


# Aliases for ergonomic access
def band_by_code(code: str, *, set_name: str = "spec_v2") -> Optional[BandSpec]:
    """Look up a band by its code in either the spec_v2 or DL/T 911 set."""
    pool = BANDS_SPEC_V2 if set_name == "spec_v2" else DL_T_911_BANDS
    for b in pool:
        if b.code == code:
            return b
    return None


def overlap_range(
    f_a: np.ndarray, f_b: np.ndarray
) -> tuple[float, float, float]:
    """Return ``(f_low, f_high, overlap_fraction)`` for two frequency arrays.

    overlap_fraction is the smaller of the two coverage ratios, expressed
    as a value in [0, 1]. Spec v2 §7.1 refuses comparison if it falls
    below 0.8 — see ``resample.py``.
    """
    f_a = np.asarray(f_a, dtype=float)
    f_b = np.asarray(f_b, dtype=float)
    a_lo, a_hi = float(f_a.min()), float(f_a.max())
    b_lo, b_hi = float(f_b.min()), float(f_b.max())
    f_lo = max(a_lo, b_lo)
    f_hi = min(a_hi, b_hi)
    if f_hi <= f_lo:
        return f_lo, f_hi, 0.0
    span_a = a_hi - a_lo
    span_b = b_hi - b_lo
    overlap = f_hi - f_lo
    return f_lo, f_hi, min(overlap / span_a, overlap / span_b)


__all__ = [
    "BANDS_SPEC_V2",
    "BandSpec",
    "DL_T_911_BANDS",
    "band_by_code",
    "overlap_range",
]
