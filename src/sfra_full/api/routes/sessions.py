"""POST /api/transformers/{id}/sessions · GET /api/sessions/{id} ·
POST /api/sessions/{id}/upload — single-trace AND batch FRAX both work
via this one endpoint (spec v2 §6.1)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfra_full.api.deps import get_session, get_storage
from sfra_full.api.schemas import (
    TestSessionCreate,
    TestSessionOut,
    TraceOut,
    UploadResponse,
)
from sfra_full.db import (
    Combination,
    OverhaulCycle,
    SourceFormat,
    TestSession,
    Trace,
    TraceRole,
    Transformer,
)
from sfra_full.db.array_helpers import array_to_bytes
from sfra_full.sfra_analysis.io import parse_file
from sfra_full.storage import FilesystemStorage


router = APIRouter(tags=["sessions"])


@router.post(
    "/api/transformers/{transformer_id}/sessions",
    response_model=TestSessionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    transformer_id: str,
    payload: TestSessionCreate,
    session: Session = Depends(get_session),
) -> TestSession:
    t = session.get(Transformer, transformer_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transformer not found")
    cycle = session.get(OverhaulCycle, payload.overhaul_cycle_id)
    if cycle is None or cycle.transformer_id != transformer_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "overhaul_cycle_id must belong to this transformer",
        )
    ts = TestSession(transformer_id=transformer_id, **payload.model_dump())
    session.add(ts)
    session.commit()
    session.refresh(ts)
    return ts


@router.get("/api/sessions/{session_id}", response_model=TestSessionOut)
def get_session_detail(
    session_id: str, session: Session = Depends(get_session)
) -> TestSession:
    ts = session.get(TestSession, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return ts


@router.post(
    "/api/sessions/{session_id}/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_to_session(
    session_id: str,
    file: UploadFile = File(...),
    role: TraceRole = Form(TraceRole.TESTED),
    combination_code: Optional[str] = Form(None),
    tap_position_current: Optional[int] = Form(None),
    tap_position_previous: Optional[int] = Form(None),
    tap_position_reference: Optional[int] = Form(None),
    detc_tap_position: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    uploaded_by: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    storage: FilesystemStorage = Depends(get_storage),
) -> UploadResponse:
    """Spec v2 §6.1: ONE endpoint handles both upload paths.

    - Single-trace: caller passes ``combination_code`` to bind to a row.
    - Batch FRAX: caller leaves ``combination_code=None``; the parser
      auto-explodes and the resolver maps each sweep to its catalogue
      code. Sweeps that don't resolve are returned in ``unmapped_sweeps``
      so the UI can prompt for manual assignment.

    Tap positions provided in the form apply to single-trace uploads.
    For batch FRAX, taps are pulled from each sweep's ``<Properties>``.
    """
    ts = session.get(TestSession, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    content = file.file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty upload")

    try:
        fmt, sweeps = parse_file(content, source_filename=file.filename or "upload")
    except Exception as exc:  # noqa: BLE001 — surface parse failures cleanly
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Parse error: {exc}"
        ) from exc

    if not sweeps:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No sweeps found in file")

    transformer = session.get(Transformer, ts.transformer_id)
    cycle = session.get(OverhaulCycle, ts.overhaul_cycle_id)
    assert transformer is not None and cycle is not None  # FK enforced

    persisted: list[Trace] = []
    unmapped: list[dict] = []

    for idx, sweep in enumerate(sweeps):
        # Resolve combination code: caller override > parser-resolved > unmapped
        code = combination_code if combination_code else sweep.combination_code
        combo: Optional[Combination] = None
        if code:
            combo = session.scalar(
                select(Combination)
                .where(Combination.transformer_type == transformer.transformer_type)
                .where(Combination.code == code)
            )
            if combo is None and not combination_code:
                # Sweep resolver suggested a code that isn't seeded for this
                # transformer type — log for UI prompt instead of failing.
                unmapped.append(
                    {
                        "sweep_index": idx,
                        "label": sweep.label,
                        "suggested_code": code,
                        "reason": "code not in catalogue for this transformer type",
                    }
                )
                code = None

        if code is None and combination_code is None:
            unmapped.append(
                {
                    "sweep_index": idx,
                    "label": sweep.label,
                    "suggested_code": None,
                    "reason": "no combination_code resolved",
                }
            )

        # Persist raw upload bytes per the spec v2 storage layout.
        blob = storage.store(
            transformer_serial=transformer.serial_no,
            overhaul_cycle_no=cycle.cycle_no,
            combination_code=code,
            role=role.value,
            original_filename=file.filename or "upload",
            content=content,
        )

        try:
            fmt_enum = SourceFormat(sweep.source_format)
        except ValueError:
            fmt_enum = SourceFormat.CSV

        trace = Trace(
            test_session_id=session_id,
            combination_id=combo.id if combo else None,
            role=role,
            label=sweep.label or f"sweep-{idx}",
            tap_position_current=_to_int(sweep.tap_current) or tap_position_current,
            tap_position_previous=_to_int(sweep.tap_previous) or tap_position_previous,
            tap_position_reference=tap_position_reference,
            detc_tap_position=_to_int(sweep.detc_tap) or detc_tap_position,
            source_file_path=str(blob.relative_path),
            source_file_format=fmt_enum,
            source_file_sha256=blob.sha256,
            sweep_index_in_source_file=idx,
            frequency_hz=array_to_bytes(sweep.frequency_hz),
            magnitude_db=array_to_bytes(sweep.magnitude_db),
            phase_deg=array_to_bytes(sweep.phase_deg),
            point_count=int(sweep.frequency_hz.size),
            freq_min_hz=float(sweep.frequency_hz.min()),
            freq_max_hz=float(sweep.frequency_hz.max()),
            uploaded_by=uploaded_by,
            notes=notes,
        )
        session.add(trace)
        persisted.append(trace)

    session.commit()
    for t in persisted:
        session.refresh(t)

    return UploadResponse(
        detected_format=fmt,
        n_sweeps_parsed=len(sweeps),
        n_traces_persisted=len(persisted),
        traces=[TraceOut.model_validate(t) for t in persisted],
        unmapped_sweeps=unmapped,
    )


def _to_int(v: object) -> Optional[int]:
    """Best-effort coercion from FRAX tap strings ('Max', 'Out', '5')."""
    if v is None:
        return None
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return None
