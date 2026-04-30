"""Tests for sfra_analysis.bands — YAML-loaded band definitions."""
from __future__ import annotations

import numpy as np

from sfra_full.sfra_analysis.bands import (
    BANDS_SPEC_V2,
    DL_T_911_BANDS,
    band_by_code,
    overlap_range,
)


def test_spec_v2_has_four_bands() -> None:
    """Spec v2 §7.2: LOW / MID_L / MID / HIGH (HIGH_EXT optional, dropped)."""
    codes = [b.code for b in BANDS_SPEC_V2]
    assert codes == ["LOW", "MID_L", "MID", "HIGH"]


def test_spec_v2_band_ranges() -> None:
    by = {b.code: b for b in BANDS_SPEC_V2}
    assert (by["LOW"].min_hz, by["LOW"].max_hz) == (20.0, 2_000.0)
    assert (by["MID_L"].min_hz, by["MID_L"].max_hz) == (2_000.0, 20_000.0)
    assert (by["MID"].min_hz, by["MID"].max_hz) == (20_000.0, 400_000.0)
    assert (by["HIGH"].min_hz, by["HIGH"].max_hz) == (400_000.0, 1_000_000.0)


def test_dlt_911_bands() -> None:
    codes = [b.code for b in DL_T_911_BANDS]
    assert codes == ["RLW", "RLM", "RLH"]


def test_band_lookup() -> None:
    assert band_by_code("MID").min_hz == 20_000.0
    assert band_by_code("RLM", set_name="dl_t_911").max_hz == 600_000.0
    assert band_by_code("DOES_NOT_EXIST") is None


def test_band_mask_and_slice() -> None:
    f = np.array([10.0, 100.0, 5_000.0, 500_000.0])
    m = np.array([1.0, 2.0, 3.0, 4.0])
    low = band_by_code("LOW")
    f_low, m_low = low.slice(f, m)
    assert list(f_low) == [100.0]
    assert list(m_low) == [2.0]


def test_overlap_range_full_overlap() -> None:
    f = np.logspace(2, 6, 100)
    f_lo, f_hi, frac = overlap_range(f, f)
    assert f_lo == 100.0
    assert f_hi == 1_000_000.0
    assert frac == 1.0


def test_overlap_range_partial() -> None:
    a = np.logspace(1, 5, 100)  # 10 to 100k
    b = np.logspace(3, 7, 100)  # 1k to 10M
    _, _, frac = overlap_range(a, b)
    assert 0.0 < frac < 1.0
