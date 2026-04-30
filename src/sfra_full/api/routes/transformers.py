"""POST /api/transformers · GET /api/transformers · POST cycles."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfra_full.api.deps import get_session
from sfra_full.api.schemas import (
    OverhaulCycleCreate,
    OverhaulCycleOut,
    TransformerCreate,
    TransformerOut,
)
from sfra_full.db import OverhaulCycle, Transformer


router = APIRouter(prefix="/api/transformers", tags=["transformers"])


@router.post("", response_model=TransformerOut, status_code=status.HTTP_201_CREATED)
def create_transformer(
    payload: TransformerCreate, session: Session = Depends(get_session)
) -> Transformer:
    existing = session.scalar(
        select(Transformer).where(Transformer.serial_no == payload.serial_no)
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Transformer with serial_no={payload.serial_no!r} already exists",
        )
    t = Transformer(**payload.model_dump())
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@router.get("", response_model=list[TransformerOut])
def list_transformers(
    session: Session = Depends(get_session),
    substation: Optional[str] = None,
    transformer_type: Optional[str] = None,
) -> list[Transformer]:
    stmt = select(Transformer).order_by(Transformer.created_at.desc())
    if substation:
        stmt = stmt.where(Transformer.substation == substation)
    if transformer_type:
        stmt = stmt.where(Transformer.transformer_type == transformer_type)
    return list(session.scalars(stmt))


@router.get("/{transformer_id}", response_model=TransformerOut)
def get_transformer(
    transformer_id: str, session: Session = Depends(get_session)
) -> Transformer:
    t = session.get(Transformer, transformer_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transformer not found")
    return t


@router.post(
    "/{transformer_id}/cycles",
    response_model=OverhaulCycleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_cycle(
    transformer_id: str,
    payload: OverhaulCycleCreate,
    session: Session = Depends(get_session),
) -> OverhaulCycle:
    """Open a new overhaul cycle, automatically closing any prior open cycle.

    Spec v2 §3 invariant: at most one open cycle per transformer.
    """
    t = session.get(Transformer, transformer_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transformer not found")

    existing_cycles = list(
        session.scalars(
            select(OverhaulCycle)
            .where(OverhaulCycle.transformer_id == transformer_id)
            .order_by(OverhaulCycle.cycle_no.desc())
        )
    )
    next_no = (existing_cycles[0].cycle_no + 1) if existing_cycles else 1

    # Close any currently open cycle on the day the new one opens (spec v2 §3).
    for c in existing_cycles:
        if c.cycle_end_date is None:
            c.cycle_end_date = payload.cycle_start_date

    cycle = OverhaulCycle(
        transformer_id=transformer_id,
        cycle_no=next_no,
        cycle_start_date=payload.cycle_start_date,
        intervention_type=payload.intervention_type,
        remarks=payload.remarks,
    )
    session.add(cycle)
    t.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(cycle)
    return cycle


@router.get("/{transformer_id}/cycles", response_model=list[OverhaulCycleOut])
def list_cycles(
    transformer_id: str, session: Session = Depends(get_session)
) -> list[OverhaulCycle]:
    t = session.get(Transformer, transformer_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transformer not found")
    return list(
        session.scalars(
            select(OverhaulCycle)
            .where(OverhaulCycle.transformer_id == transformer_id)
            .order_by(OverhaulCycle.cycle_no)
        )
    )
