"""GET /api/standards/* — combination catalogue + band/threshold tables.

Pulls from the seeded ``combination`` table when populated; otherwise falls
back to the YAML file directly so the endpoint works even on a fresh
deployment that hasn't run ``seed_combinations.py`` yet.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfra_full.api.deps import get_session
from sfra_full.api.schemas import CombinationOut
from sfra_full.db import Combination, TransformerType


router = APIRouter(prefix="/api/standards", tags=["standards"])

_CATALOGUE_PATH = (
    Path(__file__).resolve().parents[4]
    / "standards"
    / "ieee_c57_149_combinations.yaml"
)


@router.get("/combinations", response_model=list[CombinationOut])
def list_combinations(
    transformer_type: TransformerType,
    session: Session = Depends(get_session),
) -> list[CombinationOut]:
    """List the combinations applicable to a transformer type.

    Source order: ``combination`` table (if seeded) → YAML fallback.
    """
    rows = session.scalars(
        select(Combination)
        .where(Combination.transformer_type == transformer_type)
        .order_by(Combination.sequence)
    ).all()
    if rows:
        return [CombinationOut.model_validate(r) for r in rows]

    # Fallback: read from YAML so a fresh DB still answers usefully.
    data = yaml.safe_load(_CATALOGUE_PATH.read_text(encoding="utf-8"))
    spec = data.get("transformer_types", {}).get(transformer_type.value, {})
    out: list[CombinationOut] = []
    for raw in spec.get("combinations") or []:
        out.append(
            CombinationOut(
                id=0,  # synthetic — not in DB yet
                transformer_type=transformer_type,
                code=raw["code"],
                sequence=int(raw["sequence"]),
                category=raw["category"],
                winding=raw["winding"],
                phase=raw["phase"],
                injection_terminal=raw["injection_terminal"],
                measurement_terminal=raw["measurement_terminal"],
                shorted_terminals=list(raw.get("shorted_terminals") or []),
                grounded_terminals=list(raw.get("grounded_terminals") or []),
                description=raw.get("description"),
            )
        )
    if not out:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No combinations registered for {transformer_type.value} (pending Phase 1 review).",
        )
    return out


@router.get("/bands")
def list_bands() -> dict:
    """Spec v2 §7.2 + DL/T 911 sub-bands + thresholds — straight from YAML."""
    data = yaml.safe_load(_CATALOGUE_PATH.read_text(encoding="utf-8"))
    return {
        "bands": data.get("bands", {}),
        "dl_t_911_thresholds": data.get("dl_t_911_thresholds", {}),
    }
