"""Analysis runner — Mode 1 / Mode 2 dispatch.

Single entry point used by the API, CLI, and report builder:

    run(tested, reference=None, *, transformer_type=None, combination_code=None)
        → AnalysisOutcome

Behaviour:
    reference is not None  → Mode 1 (comparative)
    reference is None      → Mode 2 (reference_missing_analysis)

Spec v2 §6.2 invariant: a single tested trace MUST always produce a full
analysis result — Mode 2 ensures this even before any reference exists.
When a reference becomes available later, the caller re-invokes ``run``
with both arguments and the new (Mode 1) AnalysisOutcome supersedes the
previous standalone one in the database / UI.
"""
from __future__ import annotations

from typing import Optional

from .compare import compare
from .result_types import AnalysisMode, AnalysisOutcome, TraceData
from .standalone import analyse_standalone


def run(
    tested: TraceData,
    reference: Optional[TraceData] = None,
    *,
    transformer_type: Optional[str] = None,
    combination_code: Optional[str] = None,
) -> AnalysisOutcome:
    """Dispatch to the appropriate analysis mode and return one envelope."""
    if reference is not None:
        comparative = compare(reference, tested)
        return AnalysisOutcome(
            mode=AnalysisMode.COMPARATIVE,
            transformer_type=transformer_type,
            combination_code=combination_code,
            tested_label=tested.label,
            reference_label=reference.label,
            comparative=comparative,
        )

    standalone = analyse_standalone(tested)
    return AnalysisOutcome(
        mode=AnalysisMode.REFERENCE_MISSING,
        transformer_type=transformer_type,
        combination_code=combination_code,
        tested_label=tested.label,
        reference_label=None,
        standalone=standalone,
    )


__all__ = ["run"]
