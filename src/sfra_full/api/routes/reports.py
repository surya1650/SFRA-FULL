"""POST /api/sessions/{id}/report.{pdf,xlsx} — spec v2 §10.

Renders the session PDF or XLSX using the Phase 2 report generators.
Reports always render — partial sets are stamped with a DRAFT watermark
(spec v2 §11 non-blocking rule).
"""
from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfra_full.api.deps import get_session
from sfra_full.db import (
    AnalysisResult,
    Combination,
    OverhaulCycle,
    TestSession,
    Trace,
    TransformerType,
)
from sfra_full.reports import build_session_pdf, build_session_xlsx


router = APIRouter(prefix="/api/sessions", tags=["reports"])


_CATALOGUE_PATH = (
    Path(__file__).resolve().parents[4]
    / "standards"
    / "ieee_c57_149_combinations.yaml"
)


def _expected_total(t_type: TransformerType) -> int:
    data = yaml.safe_load(_CATALOGUE_PATH.read_text(encoding="utf-8"))
    spec = data.get("transformer_types", {}).get(t_type.value, {})
    total = spec.get("total")
    return int(total) if isinstance(total, int) else 0


def _gather(session: Session, session_id: str):
    ts = session.get(TestSession, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    transformer = ts.transformer
    cycle = ts.overhaul_cycle
    if transformer is None or cycle is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Session has no parents")

    analyses = list(
        session.scalars(
            select(AnalysisResult).where(AnalysisResult.test_session_id == session_id)
        )
    )
    combinations = list(
        session.scalars(
            select(Combination).where(
                Combination.transformer_type == transformer.transformer_type
            )
        )
    )
    return ts, transformer, cycle, analyses, combinations


@router.get("/{session_id}/report.pdf")
def session_report_pdf(
    session_id: str, session: Session = Depends(get_session)
) -> Response:
    ts, transformer, cycle, analyses, combinations = _gather(session, session_id)
    pdf_bytes = build_session_pdf(
        transformer=transformer,
        cycle=cycle,
        session=ts,
        analyses=analyses,
        combinations=combinations,
        expected_total=_expected_total(transformer.transformer_type),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="sfra-{transformer.serial_no}-{ts.session_date}.pdf"'
        },
    )


@router.get("/{session_id}/report.xlsx")
def session_report_xlsx(
    session_id: str, session: Session = Depends(get_session)
) -> Response:
    ts, transformer, cycle, analyses, combinations = _gather(session, session_id)

    # Pre-load the traces referenced by analyses to avoid per-row queries
    # in the XLSX builder.
    trace_ids: set[str] = set()
    for a in analyses:
        trace_ids.add(a.tested_trace_id)
        if a.reference_trace_id:
            trace_ids.add(a.reference_trace_id)
    traces = (
        list(session.scalars(select(Trace).where(Trace.id.in_(trace_ids))))
        if trace_ids
        else []
    )
    traces_by_id = {t.id: t for t in traces}

    xlsx_bytes = build_session_xlsx(
        transformer=transformer,
        cycle=cycle,
        session=ts,
        analyses=analyses,
        combinations=combinations,
        traces_by_id=traces_by_id,
        expected_total=_expected_total(transformer.transformer_type),
    )
    return Response(
        content=xlsx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="sfra-{transformer.serial_no}-{ts.session_date}.xlsx"'
        },
    )
