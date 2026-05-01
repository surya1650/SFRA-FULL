"""POST /api/sessions/{id}/analyse · GET /api/analyses/{id}.

Spec v2 §6.2 + Mode 2 directive:

    For every TESTED trace in the session, find its REFERENCE counterpart
    in the active overhaul cycle (matched by combination_code). If a
    reference exists → run Mode 1 (comparative). If not → run Mode 2
    (reference_missing_analysis). Either way, persist a row.

Idempotent: re-running yields one AnalysisResult per tested trace,
replacing the previous row for that trace.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfra_full import __version__
from sfra_full.api.deps import get_session
from sfra_full.api.schemas import AnalysisResultOut, RunAnalysisResponse
from sfra_full.db import (
    AnalysisModeDB,
    AnalysisResult,
    OverhaulCycle,
    SeverityDB,
    TestSession,
    Trace,
    TraceRole,
)
from sfra_full.db.array_helpers import bytes_to_array
from sfra_full.db.enums import mode_to_db, severity_to_db
from sfra_full.sfra_analysis.result_types import AnalysisMode, TraceData
from sfra_full.sfra_analysis.runner import run as run_analysis


router = APIRouter(tags=["analyses"])


def _trace_to_data(t: Trace) -> TraceData:
    f = bytes_to_array(t.frequency_hz)
    m = bytes_to_array(t.magnitude_db)
    p = bytes_to_array(t.phase_deg)
    assert f is not None and m is not None
    return TraceData(
        frequency_hz=f, magnitude_db=m, phase_deg=p, label=t.label, metadata={"id": t.id}
    )


def _find_reference_in_cycle(
    session: Session, *, cycle_id: str, combination_id: Optional[int]
) -> Optional[Trace]:
    if combination_id is None:
        return None
    return session.scalar(
        select(Trace)
        .join(TestSession, Trace.test_session_id == TestSession.id)
        .where(TestSession.overhaul_cycle_id == cycle_id)
        .where(Trace.role == TraceRole.REFERENCE)
        .where(Trace.combination_id == combination_id)
        .order_by(Trace.uploaded_at.desc())
    )


def _persist_outcome(
    session: Session,
    *,
    test_session_id: str,
    tested: Trace,
    reference: Optional[Trace],
    outcome,
) -> AnalysisResult:
    payload = outcome.to_dict()
    indicators_json = None
    resonances_json = None
    poles_json = None
    standalone_json = None
    if outcome.mode == AnalysisMode.COMPARATIVE and outcome.comparative is not None:
        indicators_json = {
            "per_band": payload["comparative"]["band_indices"],
            "full_band": payload["comparative"]["full_band_indices"],
            "band_severity": {
                k: v for k, v in payload["comparative"]["band_severity"].items()
            },
            "n_matched": payload["comparative"]["n_matched"],
            "n_lost": payload["comparative"]["n_lost"],
            "n_new": payload["comparative"]["n_new"],
        }
        resonances_json = payload["comparative"]["resonance_pairs"]
        poles_json = {
            "ref": payload["comparative"]["poles_ref"],
            "test": payload["comparative"]["poles_test"],
        }
    elif outcome.mode == AnalysisMode.REFERENCE_MISSING and outcome.standalone is not None:
        standalone_json = payload["standalone"]
        resonances_json = payload["standalone"]["resonances"]

    # Replace any prior result for this tested trace (idempotent re-runs).
    existing = session.scalar(
        select(AnalysisResult).where(AnalysisResult.tested_trace_id == tested.id)
    )
    if existing is not None:
        session.delete(existing)
        session.flush()

    ar = AnalysisResult(
        test_session_id=test_session_id,
        combination_id=tested.combination_id,
        tested_trace_id=tested.id,
        reference_trace_id=reference.id if reference else None,
        mode=mode_to_db(outcome.mode),
        severity=severity_to_db(outcome.severity),
        indicators_json=indicators_json,
        resonances_json=resonances_json,
        poles_json=poles_json,
        standalone_json=standalone_json,
        auto_remarks=outcome.auto_remarks,
        engine_version=__version__,
    )
    session.add(ar)
    session.flush()
    return ar


@router.post(
    "/api/sessions/{session_id}/analyse", response_model=RunAnalysisResponse
)
def analyse_session(
    session_id: str, session: Session = Depends(get_session)
) -> RunAnalysisResponse:
    """Run Mode 1 / Mode 2 over every TESTED trace in the session."""
    ts = session.get(TestSession, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    cycle = session.get(OverhaulCycle, ts.overhaul_cycle_id)
    if cycle is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Session has no cycle")

    tested_traces = list(
        session.scalars(
            select(Trace)
            .where(Trace.test_session_id == session_id)
            .where(Trace.role == TraceRole.TESTED)
            .order_by(Trace.uploaded_at)
        )
    )

    results: list[AnalysisResult] = []
    mode_1 = 0
    mode_2 = 0

    for tested in tested_traces:
        reference = _find_reference_in_cycle(
            session, cycle_id=cycle.id, combination_id=tested.combination_id
        )
        outcome = run_analysis(
            _trace_to_data(tested),
            reference=_trace_to_data(reference) if reference else None,
            transformer_type=ts.transformer.transformer_type.value
            if ts.transformer
            else None,
            combination_code=tested.combination.code if tested.combination else None,
        )
        ar = _persist_outcome(
            session,
            test_session_id=session_id,
            tested=tested,
            reference=reference,
            outcome=outcome,
        )
        results.append(ar)
        if outcome.mode == AnalysisMode.COMPARATIVE:
            mode_1 += 1
        else:
            mode_2 += 1

    session.commit()
    for r in results:
        session.refresh(r)

    return RunAnalysisResponse(
        n_results=len(results),
        mode_1_count=mode_1,
        mode_2_count=mode_2,
        results=[AnalysisResultOut.model_validate(r) for r in results],
    )


@router.get("/api/analyses/{analysis_id}", response_model=AnalysisResultOut)
def get_analysis(
    analysis_id: str, session: Session = Depends(get_session)
) -> AnalysisResult:
    ar = session.get(AnalysisResult, analysis_id)
    if ar is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return ar


@router.get(
    "/api/sessions/{session_id}/analyses",
    response_model=list[AnalysisResultOut],
)
def list_analyses_for_session(
    session_id: str, session: Session = Depends(get_session)
) -> list[AnalysisResult]:
    ts = session.get(TestSession, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return list(
        session.scalars(
            select(AnalysisResult)
            .where(AnalysisResult.test_session_id == session_id)
            .order_by(AnalysisResult.computed_at.desc())
        )
    )
