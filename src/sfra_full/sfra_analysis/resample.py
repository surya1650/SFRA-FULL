"""Common-frequency-axis re-gridding for trace comparison.

Implements spec v2 §7.1 verbatim:

1. Determine overlap.
2. Refuse comparison if overlap < 80% of either trace's span.
3. Build a 1000-point logarithmically spaced grid.
4. Interpolate magnitude (in dB) and unwrapped phase via PCHIP.
5. Caller caches the result on the AnalysisResult.

This module is deliberately stateless and side-effect-free so it can be
unit-tested in isolation against synthetic vectors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.interpolate import PchipInterpolator

from .bands import overlap_range


SPEC_V2_OVERLAP_THRESHOLD = 0.80
SPEC_V2_DEFAULT_GRID_POINTS = 1000


class InsufficientOverlapError(ValueError):
    """Raised when two traces share too little frequency range to compare.

    Surfaces actual overlap percentages so the UI can quote them.
    """

    def __init__(self, frac_a: float, frac_b: float, threshold: float) -> None:
        self.frac_a = frac_a
        self.frac_b = frac_b
        self.threshold = threshold
        super().__init__(
            f"Trace overlap below threshold {threshold:.0%}: "
            f"reference covers {frac_a:.1%}, tested covers {frac_b:.1%}"
        )


@dataclass(slots=True)
class ResampledPair:
    """Two traces re-gridded onto a shared log-frequency axis."""

    frequency_hz: np.ndarray   # shape (N,), log-spaced
    ref_magnitude_db: np.ndarray
    test_magnitude_db: np.ndarray
    ref_phase_deg: Optional[np.ndarray]
    test_phase_deg: Optional[np.ndarray]
    overlap_fraction: float    # min(coverage_ref, coverage_test) in [0,1]
    f_low: float
    f_high: float

    @property
    def n_points(self) -> int:
        return int(self.frequency_hz.size)


def _pchip_eval(
    x_src: np.ndarray, y_src: np.ndarray, x_target: np.ndarray
) -> np.ndarray:
    """Stable monotone-aware PCHIP evaluation, sorted+deduplicated."""
    order = np.argsort(x_src)
    xs = x_src[order]
    ys = y_src[order]
    # Drop duplicate x's (PCHIP requires strictly increasing x).
    keep = np.concatenate([[True], np.diff(xs) > 0])
    xs = xs[keep]
    ys = ys[keep]
    return PchipInterpolator(xs, ys, extrapolate=False)(x_target)


def regrid_pair(
    f_ref: np.ndarray,
    mag_ref_db: np.ndarray,
    f_test: np.ndarray,
    mag_test_db: np.ndarray,
    phase_ref_deg: Optional[np.ndarray] = None,
    phase_test_deg: Optional[np.ndarray] = None,
    *,
    n_points: int = SPEC_V2_DEFAULT_GRID_POINTS,
    overlap_threshold: float = SPEC_V2_OVERLAP_THRESHOLD,
) -> ResampledPair:
    """Resample two traces onto a shared 1000-point log grid.

    Spec v2 §7.1 step-by-step. Phase, when present, is unwrapped first
    (in radians, then converted back to degrees) before interpolation
    so PCHIP doesn't see phase wraps.

    Raises ``InsufficientOverlapError`` if either trace covers less
    than ``overlap_threshold`` of the candidate common range.
    """
    f_ref = np.asarray(f_ref, dtype=float)
    mag_ref_db = np.asarray(mag_ref_db, dtype=float)
    f_test = np.asarray(f_test, dtype=float)
    mag_test_db = np.asarray(mag_test_db, dtype=float)

    f_lo, f_hi, frac_min = overlap_range(f_ref, f_test)

    span_ref = f_ref.max() - f_ref.min()
    span_test = f_test.max() - f_test.min()
    coverage_ref = (f_hi - f_lo) / span_ref if span_ref > 0 else 0.0
    coverage_test = (f_hi - f_lo) / span_test if span_test > 0 else 0.0
    if coverage_ref < overlap_threshold or coverage_test < overlap_threshold:
        raise InsufficientOverlapError(coverage_ref, coverage_test, overlap_threshold)

    if f_lo <= 0:
        raise ValueError("Frequencies must be > 0 for log-spaced re-grid")

    f_grid = np.logspace(np.log10(f_lo), np.log10(f_hi), n_points)

    mag_ref_i = _pchip_eval(f_ref, mag_ref_db, f_grid)
    mag_test_i = _pchip_eval(f_test, mag_test_db, f_grid)

    phase_ref_i: Optional[np.ndarray] = None
    phase_test_i: Optional[np.ndarray] = None
    if phase_ref_deg is not None and len(phase_ref_deg) == len(f_ref):
        unwrapped = np.unwrap(np.deg2rad(np.asarray(phase_ref_deg, dtype=float)))
        phase_ref_i = np.rad2deg(_pchip_eval(f_ref, unwrapped, f_grid))
    if phase_test_deg is not None and len(phase_test_deg) == len(f_test):
        unwrapped = np.unwrap(np.deg2rad(np.asarray(phase_test_deg, dtype=float)))
        phase_test_i = np.rad2deg(_pchip_eval(f_test, unwrapped, f_grid))

    return ResampledPair(
        frequency_hz=f_grid,
        ref_magnitude_db=mag_ref_i,
        test_magnitude_db=mag_test_i,
        ref_phase_deg=phase_ref_i,
        test_phase_deg=phase_test_i,
        overlap_fraction=min(coverage_ref, coverage_test),
        f_low=f_lo,
        f_high=f_hi,
    )


__all__ = [
    "InsufficientOverlapError",
    "ResampledPair",
    "SPEC_V2_DEFAULT_GRID_POINTS",
    "SPEC_V2_OVERLAP_THRESHOLD",
    "regrid_pair",
]
