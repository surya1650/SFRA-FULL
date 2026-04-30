"""Tests for sfra_analysis.runner — Mode 1 / Mode 2 dispatch.

Confirms spec v2 §6.2: a single tested trace MUST always produce a full
analysis result, regardless of whether a reference is supplied.
"""
from __future__ import annotations

import numpy as np

from sfra_full.sfra_analysis.result_types import (
    AnalysisMode,
    Severity,
    TraceData,
)
from sfra_full.sfra_analysis.runner import run


def _make_trace(factory, **kwargs) -> TraceData:
    f, m, p = factory(**kwargs)
    return TraceData(frequency_hz=f, magnitude_db=m, phase_deg=p, label="test")


def test_mode2_dispatched_when_reference_missing(synthetic_trace_factory) -> None:
    """No reference → Mode 2 (reference_missing_analysis)."""
    tested = _make_trace(synthetic_trace_factory, seed=1)
    out = run(tested)
    assert out.mode == AnalysisMode.REFERENCE_MISSING
    assert out.standalone is not None
    assert out.comparative is None
    assert out.severity in {Severity.APPEARS_NORMAL, Severity.SUSPECT, Severity.INDETERMINATE}
    # Per directive: emit a remark even without reference.
    assert out.auto_remarks
    assert "no reference" in out.auto_remarks.lower()


def test_mode1_dispatched_when_reference_present(synthetic_trace_factory) -> None:
    """Reference + tested → Mode 1 (comparative)."""
    ref = _make_trace(synthetic_trace_factory, seed=1)
    tested = _make_trace(synthetic_trace_factory, seed=2, noise=0.05)
    out = run(tested, reference=ref)
    assert out.mode == AnalysisMode.COMPARATIVE
    assert out.comparative is not None
    assert out.standalone is None
    # All Mode 1 severities are spec-grade.
    assert out.severity in {
        Severity.NORMAL,
        Severity.MINOR_DEVIATION,
        Severity.SIGNIFICANT_DEVIATION,
        Severity.SEVERE_DEVIATION,
    }
    assert out.auto_remarks


def test_severity_escalates_with_resonance_shift(synthetic_trace_factory) -> None:
    """A 12% frequency shift must escalate severity to SEVERE."""
    ref = _make_trace(synthetic_trace_factory, shift=0.0, seed=1)
    tested = _make_trace(synthetic_trace_factory, shift=0.12, seed=1, noise=0.05)
    out = run(tested, reference=ref)
    assert out.mode == AnalysisMode.COMPARATIVE
    assert out.severity == Severity.SEVERE_DEVIATION
    assert out.comparative.n_lost + out.comparative.n_new >= 3


def test_to_dict_is_json_friendly(synthetic_trace_factory) -> None:
    """AnalysisOutcome.to_dict() must produce JSON-encodable output."""
    import json
    tested = _make_trace(synthetic_trace_factory, seed=1)
    out = run(tested)
    payload = out.to_dict()
    s = json.dumps(payload)
    assert '"mode"' in s
    assert '"severity"' in s


def test_metadata_preserved_in_outcome(synthetic_trace_factory) -> None:
    tested = _make_trace(synthetic_trace_factory, seed=1)
    out = run(
        tested,
        transformer_type="TWO_WINDING",
        combination_code="EEOC_HV_R",
    )
    assert out.transformer_type == "TWO_WINDING"
    assert out.combination_code == "EEOC_HV_R"
