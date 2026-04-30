"""SFRA analysis engine — Mode 1 (comparative) and Mode 2 (standalone).

Public API:
    run(reference, tested, *, transformer_type, combination_code) -> AnalysisOutcome

The runner dispatches:
    - Mode 1 (comparative)  — when ``reference`` is provided
    - Mode 2 (standalone)   — when ``reference is None`` (reference_missing_analysis)

Both modes return a unified ``AnalysisOutcome`` discriminated by ``mode`` so
downstream code (DB, reports, UI) can render either path with one code path.
"""
from __future__ import annotations

from .bands import BANDS_SPEC_V2, DL_T_911_BANDS, BandSpec
from .result_types import (
    AnalysisMode,
    AnalysisOutcome,
    BandIndices,
    ComparativeResult,
    Severity,
    StandaloneResult,
    TraceData,
)

__all__ = [
    "AnalysisMode",
    "AnalysisOutcome",
    "BANDS_SPEC_V2",
    "BandIndices",
    "BandSpec",
    "ComparativeResult",
    "DL_T_911_BANDS",
    "Severity",
    "StandaloneResult",
    "TraceData",
]
