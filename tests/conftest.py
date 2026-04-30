"""Pytest configuration shared by all test modules."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Make src/ importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="session")
def synthetic_trace_factory():
    """Return a callable that generates a synthetic SFRA trace.

    Usage:
        f, m, p = synthetic_trace_factory(shift=0.0, noise=0.05, seed=0)
    """

    def _make(
        *,
        shift: float = 0.0,
        offset_db: float = 0.0,
        noise: float = 0.05,
        seed: int = 0,
        n_points: int = 1500,
        f_min_hz: float = 20.0,
        f_max_hz: float = 1_000_000.0,
    ):
        rng = np.random.default_rng(seed)
        f = np.logspace(np.log10(f_min_hz), np.log10(f_max_hz), n_points)
        base = -20.0 - 30 * np.tanh((np.log10(f) - 3.5) / 1.0)
        res = np.zeros_like(f)
        for fc, depth, q in [
            (12_300, 18.0, 12),
            (85_000, 14.0, 10),
            (340_000, 10.0, 8),
        ]:
            fc_shifted = fc * (1 + shift)
            res -= depth / (1.0 + ((np.log10(f) - np.log10(fc_shifted)) * q) ** 2)
        magnitude = base + res + offset_db + rng.normal(0, noise, f.size)
        # Synthetic phase: generic shape, useful for unwrap testing.
        phase = -90.0 + 40.0 * np.tanh((np.log10(f) - 4.0) / 1.0) + rng.normal(0, 0.5, f.size)
        return f, magnitude, phase

    return _make


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def upstream_samples(repo_root) -> Path:
    """Path to upstream/sample fixtures, if external/SFRA was cloned."""
    return repo_root / "external" / "SFRA" / "backend" / "samples"
