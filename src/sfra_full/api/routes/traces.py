"""GET /api/traces/{id} — return trace metadata + decoded arrays."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from sfra_full.api.deps import get_session
from sfra_full.api.schemas import TraceOut
from sfra_full.db import Trace
from sfra_full.db.array_helpers import bytes_to_array


router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("/{trace_id}", response_model=TraceOut)
def get_trace(
    trace_id: str, session: Session = Depends(get_session)
) -> Trace:
    t = session.get(Trace, trace_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trace not found")
    return t


@router.get("/{trace_id}/data")
def get_trace_data(
    trace_id: str, session: Session = Depends(get_session)
) -> dict:
    """Decode the BYTEA-stored arrays for plotting."""
    t = session.get(Trace, trace_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trace not found")
    f = bytes_to_array(t.frequency_hz)
    m = bytes_to_array(t.magnitude_db)
    p = bytes_to_array(t.phase_deg)
    return {
        "id": t.id,
        "label": t.label,
        "frequency_hz": f.tolist() if f is not None else [],
        "magnitude_db": m.tolist() if m is not None else [],
        "phase_deg": p.tolist() if p is not None else None,
        "point_count": int(t.point_count),
        "source_file_format": t.source_file_format.value,
        "source_file_sha256": t.source_file_sha256,
    }
