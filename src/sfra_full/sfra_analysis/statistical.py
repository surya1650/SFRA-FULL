"""Statistical comparison metrics — spec v2 §7.3 verbatim.

Important: spec v2's CC formula is **uncentered** cosine similarity:

    CC = sum(X·Y) / sqrt(sum(X²) · sum(Y²))

This is NOT the Pearson correlation coefficient that the upstream
``external/SFRA/backend/analysis/indices.py`` computes (that one
mean-centers the inputs). The two formulas give different numbers on
the same data — the spec's choice is recorded in DECISIONS.md.

Other metrics:
    ASLE = mean(|X-Y|)               (inputs already in dB)
    CSD  = sqrt(sum((X-Y)²) / (N-1))
    MM   = mean(min(x,y) / max(x,y)) per point
    MaxDev (dB, Hz) = (max(|X-Y|), frequency_at_argmax)
    RLx  = -log10(1 - CCx)           clamped to CC ≤ 0.99999
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .bands import BANDS_SPEC_V2, BandSpec
from .result_types import BandIndices


# Spec v2 §7.3: clamp CC near 1.0 to avoid log(0).
_CC_CLAMP_MAX = 0.99999


# ---------------------------------------------------------------------------
# Atomic metrics
# ---------------------------------------------------------------------------
def cc_uncentered(x: np.ndarray, y: np.ndarray) -> float:
    """Uncentered cosine similarity per spec v2 §7.3."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0:
        return float("nan")
    denom = np.sqrt((x * x).sum() * (y * y).sum())
    if denom <= 0.0:
        # Both vectors zero → treat as identical.
        return 1.0 if np.allclose(x, y) else float("nan")
    return float((x * y).sum() / denom)


def asle(x: np.ndarray, y: np.ndarray) -> float:
    """Absolute sum of logarithmic errors — mean(|X-Y|), inputs in dB."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0:
        return float("nan")
    return float(np.mean(np.abs(x - y)))


def csd(x: np.ndarray, y: np.ndarray) -> float:
    """Comparative standard deviation per spec v2 §7.3.

    Formula: sqrt(sum((X-Y)²) / (N-1)).  Note this is NOT the std of the
    diff series (which would subtract the mean diff first) — the spec is
    explicit about using the uncentered sum-of-squares.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 2:
        return float("nan")
    d = x - y
    return float(np.sqrt(np.sum(d * d) / (x.size - 1)))


def min_max_ratio(x: np.ndarray, y: np.ndarray) -> float:
    """Mean of point-wise min/max ratio. Robust to sign by working on
    absolute values per the upstream convention."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0:
        return float("nan")
    a = np.abs(x)
    b = np.abs(y)
    lo = np.minimum(a, b)
    hi = np.maximum(a, b)
    mask = hi > 0
    if not np.any(mask):
        return 1.0  # both zero everywhere
    return float(np.mean(lo[mask] / hi[mask]))


def max_deviation(
    x: np.ndarray, y: np.ndarray, frequency_hz: np.ndarray
) -> tuple[float, float]:
    """Return (max |X-Y| in dB, frequency_hz at that point)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size == 0:
        return float("nan"), float("nan")
    d = np.abs(x - y)
    idx = int(np.argmax(d))
    return float(d[idx]), float(frequency_hz[idx])


def rl_factor(cc: float) -> float:
    """DL/T 911 relative factor: RLx = -log10(1 - CC), clamped."""
    if cc is None or np.isnan(cc):
        return float("nan")
    cc_clamped = min(cc, _CC_CLAMP_MAX)
    cc_clamped = max(cc_clamped, -_CC_CLAMP_MAX)
    return float(-np.log10(1.0 - cc_clamped))


# ---------------------------------------------------------------------------
# Per-band aggregator
# ---------------------------------------------------------------------------
def band_indices(
    frequency_hz: np.ndarray,
    ref_db: np.ndarray,
    test_db: np.ndarray,
    band: Optional[BandSpec],
    *,
    band_code: Optional[str] = None,
) -> BandIndices:
    """Compute every metric on a single band (or full range if band=None)."""
    if band is None:
        f = np.asarray(frequency_hz, dtype=float)
        x = np.asarray(ref_db, dtype=float)
        y = np.asarray(test_db, dtype=float)
        code = band_code or "FULL"
        f_lo: Optional[float] = float(f.min()) if f.size else None
        f_hi: Optional[float] = float(f.max()) if f.size else None
    else:
        f, x, y = band.slice(frequency_hz, ref_db, test_db)
        code = band.code
        f_lo = band.min_hz
        f_hi = band.max_hz

    n = int(f.size)
    if n < 4:
        return BandIndices(
            band_code=code, f_low=f_lo, f_high=f_hi, n_points=n,
        )

    cc = cc_uncentered(x, y)
    a = asle(x, y)
    s = csd(x, y)
    mm = min_max_ratio(x, y)
    mx_db, mx_hz = max_deviation(x, y, f)
    rl = rl_factor(cc)

    return BandIndices(
        band_code=code,
        f_low=f_lo,
        f_high=f_hi,
        n_points=n,
        cc=cc,
        asle=a,
        csd=s,
        min_max_ratio=mm,
        max_dev_db=mx_db,
        max_dev_freq_hz=mx_hz,
        rl_factor=rl,
    )


def all_bands(
    frequency_hz: np.ndarray,
    ref_db: np.ndarray,
    test_db: np.ndarray,
) -> tuple[list[BandIndices], BandIndices]:
    """Compute spec-v2 per-band table + the FULL row.

    Returns ``(per_band, full)``. ``per_band`` is a list of one entry per
    band in ``BANDS_SPEC_V2`` (LOW/MID_L/MID/HIGH); ``full`` covers the
    whole frequency range.
    """
    per_band = [band_indices(frequency_hz, ref_db, test_db, b) for b in BANDS_SPEC_V2]
    full = band_indices(frequency_hz, ref_db, test_db, None, band_code="FULL")
    return per_band, full


__all__ = [
    "all_bands",
    "asle",
    "band_indices",
    "cc_uncentered",
    "csd",
    "max_deviation",
    "min_max_ratio",
    "rl_factor",
]
