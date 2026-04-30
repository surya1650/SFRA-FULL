"""Tests for sfra_analysis.statistical — spec v2 §7.3 metric formulas."""
from __future__ import annotations

import numpy as np

from sfra_full.sfra_analysis.statistical import (
    asle,
    cc_uncentered,
    csd,
    max_deviation,
    min_max_ratio,
    rl_factor,
)


def test_cc_identical_traces_is_one() -> None:
    """Identical X and Y → CC = 1.0."""
    x = np.array([-10, -20, -30, -40, -50, -60], dtype=float)
    assert cc_uncentered(x, x) == 1.0


def test_cc_uncentered_formula() -> None:
    """Spec v2 §7.3: CC = sum(X*Y) / sqrt(sum(X²)·sum(Y²)) — uncentered."""
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([2.0, 3.0, 4.0, 5.0])
    expected = float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum()))
    assert abs(cc_uncentered(x, y) - expected) < 1e-12


def test_asle_zero_for_identical() -> None:
    x = np.array([-10.0, -20.0, -30.0])
    assert asle(x, x) == 0.0


def test_asle_mean_abs_diff() -> None:
    x = np.array([0.0, 0.0, 0.0])
    y = np.array([3.0, -1.0, 2.0])
    # mean(|0-3|, |0-(-1)|, |0-2|) = (3+1+2)/3 = 2.0
    assert abs(asle(x, y) - 2.0) < 1e-12


def test_csd_uncentered_sum_of_squares() -> None:
    """Spec v2: CSD = sqrt(sum((X-Y)²)/(N-1)) — does NOT subtract mean diff."""
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = np.array([2.0, 4.0, 6.0, 8.0])
    diff = x - y
    expected = float(np.sqrt(np.sum(diff * diff) / (x.size - 1)))
    assert abs(csd(x, y) - expected) < 1e-12


def test_min_max_ratio_identical_is_one() -> None:
    x = np.array([-10.0, -20.0, -30.0])
    assert min_max_ratio(x, x) == 1.0


def test_max_deviation_locates_worst_point() -> None:
    f = np.array([100.0, 1000.0, 10000.0])
    x = np.array([-20.0, -30.0, -40.0])
    y = np.array([-21.0, -25.0, -39.0])
    # diffs: 1, 5, 1 → max at f=1000 with 5 dB
    db, hz = max_deviation(x, y, f)
    assert abs(db - 5.0) < 1e-12
    assert hz == 1000.0


def test_rl_factor_clamping() -> None:
    """RL is clamped at CC = 0.99999 (rl_max ≈ 5.0)."""
    rl = rl_factor(1.0)
    assert rl == rl_factor(0.99999)
    assert abs(rl - 5.0) < 1e-9


def test_rl_factor_severe() -> None:
    """RL drops sharply as CC degrades — sanity check the curve."""
    assert rl_factor(0.99) < rl_factor(0.999) < rl_factor(0.9999)
    assert rl_factor(0.9) < 1.05  # roughly -log10(0.1) = 1.0


def test_rl_factor_nan_in_nan_out() -> None:
    assert rl_factor(float("nan")) != rl_factor(float("nan"))  # NaN
