"""GET /api/standards/* — combination catalogue + band/threshold tables.

Pulls from the seeded ``combination`` table when populated; otherwise falls
back to the YAML file directly so the endpoint works even on a fresh
deployment that hasn't run ``seed_combinations.py`` yet.

Phase 4 additions:
- PATCH /api/standards/thresholds — admin-only hot-reload of DL/T 911
  RL thresholds. The verdict module's ``_load_thresholds`` lru_cache is
  cleared so the next analysis run picks up the new values immediately.
- GET /api/standards/thresholds — read-back of the active table.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfra_full.api.deps import get_session
from sfra_full.api.schemas import CombinationOut
from sfra_full.audit import AuditAction, record_event
from sfra_full.auth import User, require_admin
from sfra_full.db import Combination, TransformerType
from sfra_full.sfra_analysis.verdict import _load_thresholds  # type: ignore[attr-defined]


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


# ---------------------------------------------------------------------------
# Hot-reload thresholds (admin-only)
# ---------------------------------------------------------------------------
class ThresholdsPatch(BaseModel):
    """Admin-supplied DL/T 911 threshold patch.

    Shape mirrors ``dl_t_911_thresholds:`` in the catalogue YAML.
    Top-level keys: RLW / RLM / RLH; each maps to bands with min/max
    floats. The patch is deep-merged into the existing table so partial
    updates are supported (e.g. tweak only RLM.slight.min).
    """

    dl_t_911_thresholds: dict[str, Any]


@router.get("/thresholds")
def get_thresholds() -> dict:
    """Active DL/T 911 thresholds — same shape the verdict engine uses."""
    table = _load_thresholds()
    return {
        code: {
            "code": t.code,
            "normal_min": t.normal_min,
            "slight_min": t.slight_min,
            "obvious_min": t.obvious_min,
            "severe_max": t.severe_max,
            "informational_only": t.informational_only,
        }
        for code, t in table.items()
    }


@router.patch("/thresholds")
def patch_thresholds(
    payload: ThresholdsPatch,
    session: Session = Depends(get_session),
    actor: User = Depends(require_admin),
) -> dict:
    """Hot-reload thresholds without container restart.

    Persists the merged table to the YAML catalogue (so it survives
    container restarts), invalidates the verdict module's cache, and
    audits the change.
    """
    text = _CATALOGUE_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    current = dict(data.get("dl_t_911_thresholds") or {})

    merged = _deep_merge(current, payload.dl_t_911_thresholds)
    data["dl_t_911_thresholds"] = merged

    # Atomic write: temp file + rename so a crash mid-write can't corrupt
    # the catalogue.
    tmp = _CATALOGUE_PATH.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    tmp.replace(_CATALOGUE_PATH)

    # Invalidate the verdict module's lru_cache.
    _load_thresholds.cache_clear()  # type: ignore[attr-defined]

    record_event(
        session,
        action=AuditAction.THRESHOLDS_UPDATE,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        target_kind="thresholds",
        target_id="dl_t_911",
        request_method="PATCH",
        request_path="/api/standards/thresholds",
        response_status=200,
        detail={"patch_keys": list(payload.dl_t_911_thresholds.keys())},
        commit=True,
    )

    return {"updated": True, "merged_keys": sorted(merged.keys())}


def _deep_merge(base: dict, patch: dict) -> dict:
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
