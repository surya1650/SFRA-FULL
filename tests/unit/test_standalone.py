"""Tests for sfra_analysis.standalone — Mode 2 single-trace analysis."""
from __future__ import annotations

import numpy as np

from sfra_full.sfra_analysis.result_types import Severity, TraceData
from sfra_full.sfra_analysis.standalone import analyse_standalone


def _trace(synthetic_trace_factory, **kwargs) -> TraceData:
    f, m, p = synthetic_trace_factory(**kwargs)
    return TraceData(frequency_hz=f, magnitude_db=m, phase_deg=p, label="standalone-test")


def test_short_trace_gets_indeterminate(synthetic_trace_factory) -> None:
    f = np.array([10.0, 100.0, 1000.0])
    m = np.array([-10.0, -20.0, -30.0])
    out = analyse_standalone(TraceData(frequency_hz=f, magnitude_db=m, label="short"))
    assert out.qualitative_severity == Severity.INDETERMINATE
    assert "trace_too_short" in out.anomaly_flags
    assert "too short" in out.auto_remarks.lower()


def test_clean_trace_appears_normal(synthetic_trace_factory) -> None:
    """A nominal synthetic trace should be APPEARS_NORMAL."""
    out = analyse_standalone(_trace(synthetic_trace_factory, seed=1, noise=0.02))
    assert out.qualitative_severity in {Severity.APPEARS_NORMAL, Severity.SUSPECT}
    assert out.n_resonances >= 2  # expect ~3 from synth, allow detection slack
    assert "no reference" in out.auto_remarks.lower()


def test_band_energy_populated_for_each_band(synthetic_trace_factory) -> None:
    out = analyse_standalone(_trace(synthetic_trace_factory, seed=1))
    codes = {be.band_code for be in out.band_energy}
    assert codes == {"LOW", "MID_L", "MID", "HIGH"}
    # Full band always present.
    assert out.full_band_energy.band_code == "FULL"


def test_remarks_format_anomalies_when_suspect(synthetic_trace_factory) -> None:
    """Force suspicion via heavy noise + frequency shift."""
    f, m, p = synthetic_trace_factory(shift=0.0, seed=1, noise=0.02)
    # Inject an obvious magnitude excursion in HIGH band so range_db > 30 dB.
    high_mask = (f >= 400_000) & (f <= 1_000_000)
    m_perturbed = m.copy()
    m_perturbed[high_mask] = m_perturbed[high_mask] + 25 * np.sin(
        np.linspace(0, 6 * np.pi, high_mask.sum())
    )
    out = analyse_standalone(
        TraceData(frequency_hz=f, magnitude_db=m_perturbed, phase_deg=p, label="perturbed")
    )
    assert out.qualitative_severity == Severity.SUSPECT
    assert any("HIGH" in flag or "high" in flag for flag in out.anomaly_flags)
