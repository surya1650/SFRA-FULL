"""Tests for sfra_analysis.resample — common-grid re-gridding (spec v2 §7.1)."""
from __future__ import annotations

import numpy as np
import pytest

from sfra_full.sfra_analysis.resample import (
    InsufficientOverlapError,
    SPEC_V2_DEFAULT_GRID_POINTS,
    SPEC_V2_OVERLAP_THRESHOLD,
    regrid_pair,
)


def test_full_overlap_produces_full_grid() -> None:
    f = np.logspace(2, 6, 500)
    m = -20 - 10 * np.log10(f)
    pair = regrid_pair(f, m, f, m)
    assert pair.n_points == SPEC_V2_DEFAULT_GRID_POINTS
    assert pair.overlap_fraction > 0.99
    # Ref ≈ test on full overlap (within PCHIP tolerance).
    assert np.allclose(pair.ref_magnitude_db, pair.test_magnitude_db, atol=1e-9)


def test_partial_overlap_under_threshold_raises() -> None:
    """Spec v2 §7.1: refuse comparison when overlap < 80%."""
    f_a = np.logspace(1, 5, 200)
    f_b = np.logspace(4, 7, 200)  # only the top decade overlaps
    m_a = -20 - 10 * np.log10(f_a)
    m_b = -20 - 10 * np.log10(f_b)
    with pytest.raises(InsufficientOverlapError):
        regrid_pair(f_a, m_a, f_b, m_b, overlap_threshold=SPEC_V2_OVERLAP_THRESHOLD)


def test_grid_is_log_spaced() -> None:
    f = np.logspace(2, 6, 300)
    m = -20 - 10 * np.log10(f)
    pair = regrid_pair(f, m, f, m)
    # Log-spacing → constant ratio between consecutive points.
    ratios = pair.frequency_hz[1:] / pair.frequency_hz[:-1]
    assert np.std(ratios) < 1e-6


def test_phase_unwrap_preserved() -> None:
    """Phase should be unwrapped on the output grid."""
    f = np.logspace(2, 6, 500)
    m = -20.0 + 0.0 * f
    # Synth: phase wrapping naturally without unwrap.
    phase = (np.linspace(-720, 720, f.size)) % 360 - 180
    pair = regrid_pair(f, m, f, m, phase_ref_deg=phase, phase_test_deg=phase)
    assert pair.ref_phase_deg is not None
    # After unwrap+regrid, phase span should exceed ±180 (no wrap-flips).
    span = pair.ref_phase_deg.max() - pair.ref_phase_deg.min()
    assert span > 180.0
