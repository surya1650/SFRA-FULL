"""Verdict + auto-remarks engine — DL/T 911-2004 thresholds + spec v2 §7.7.

Threshold defaults are loaded from ``standards/ieee_c57_149_combinations.yaml``
``dl_t_911_thresholds`` (so engineering edits the YAML, not Python). At
runtime the thresholds can be overridden by passing a dict — the FastAPI
layer will surface that as a settings panel later.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from .result_types import BandIndices, Severity


CATALOGUE_PATH = (
    Path(__file__).resolve().parents[3]
    / "standards"
    / "ieee_c57_149_combinations.yaml"
)


# ---------------------------------------------------------------------------
# Threshold model
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class BandThresholds:
    """RL-factor thresholds for one DL/T 911 band."""

    code: str
    normal_min: Optional[float]      # >= → NORMAL
    slight_min: Optional[float]      # [slight_min, normal_min) → MINOR
    obvious_min: Optional[float]     # [obvious_min, slight_min) → SIGNIFICANT
    severe_max: Optional[float]      # < severe_max → SEVERE
    informational_only: bool = False


@lru_cache(maxsize=1)
def _load_thresholds() -> dict[str, BandThresholds]:
    with CATALOGUE_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    raw = data.get("dl_t_911_thresholds", {})
    out: dict[str, BandThresholds] = {}
    for code, spec in raw.items():
        normal = spec.get("normal", {})
        slight = spec.get("slight", {})
        obvious = spec.get("obvious", {})
        severe = spec.get("severe", {})
        out[code] = BandThresholds(
            code=code,
            normal_min=_get(normal, "min"),
            slight_min=_get(slight, "min"),
            obvious_min=_get(obvious, "min"),
            severe_max=_get(severe, "max"),
            informational_only=bool(spec.get("informational_only", False)),
        )
    return out


def _get(d: dict, key: str) -> Optional[float]:
    if not isinstance(d, dict):
        return None
    val = d.get(key)
    return float(val) if val is not None else None


# ---------------------------------------------------------------------------
# Per-band severity
# ---------------------------------------------------------------------------
def severity_for_rl(
    band_code: str,
    rl: Optional[float],
    *,
    thresholds: Optional[dict[str, "BandThresholds"]] = None,
) -> Severity:
    """Map an RL value to a spec v2 §3 Severity for a given band code.

    The catalogue uses RLW/RLM/RLH for DL/T 911. The SPEC v2 bands
    (LOW/MID_L/MID/HIGH) map onto these as:
        LOW + MID_L → RLW (overlap; LOW dominates)
        MID         → RLM
        HIGH        → RLH (informational)
    """
    if rl is None or rl != rl:  # NaN check
        return Severity.INDETERMINATE

    table: dict[str, BandThresholds] = thresholds or _load_thresholds()

    band_to_dlt = {
        "LOW": "RLW", "MID_L": "RLW",
        "MID": "RLM",
        "HIGH": "RLH",
        "FULL": "RLW",  # treat full-band RL as a LOW-band-equivalent severity
        "RLW": "RLW", "RLM": "RLM", "RLH": "RLH",
    }
    dlt = band_to_dlt.get(band_code)
    if dlt is None or dlt not in table:
        return Severity.INDETERMINATE

    spec: BandThresholds = table[dlt]
    if spec.informational_only:
        # HIGH band — informational only; only flag SEVERE if catastrophically low
        if spec.normal_min is not None and rl >= spec.normal_min:
            return Severity.NORMAL
        return Severity.MINOR_DEVIATION

    n = spec.normal_min
    s = spec.slight_min
    o = spec.obvious_min

    if n is not None and rl >= n:
        return Severity.NORMAL
    if s is not None and rl >= s:
        return Severity.MINOR_DEVIATION
    if o is not None and rl >= o:
        return Severity.SIGNIFICANT_DEVIATION
    return Severity.SEVERE_DEVIATION


# Severity ordering (worst-first) for "overall = worst-of-all-bands".
_SEVERITY_ORDER = [
    Severity.SEVERE_DEVIATION,
    Severity.SIGNIFICANT_DEVIATION,
    Severity.MINOR_DEVIATION,
    Severity.NORMAL,
    Severity.SUSPECT,
    Severity.APPEARS_NORMAL,
    Severity.INDETERMINATE,
]
_SEVERITY_RANK = {s: i for i, s in enumerate(_SEVERITY_ORDER)}


def worst_severity(values: list[Severity]) -> Severity:
    """Return the worst (lowest-rank) severity in the list."""
    if not values:
        return Severity.INDETERMINATE
    return min(values, key=lambda s: _SEVERITY_RANK.get(s, 999))


# ---------------------------------------------------------------------------
# Auto-remarks templates — spec v2 §7.7
# ---------------------------------------------------------------------------
ROOT_CAUSE_HINTS = {
    "LOW":   "core or core-grounding issue (residual magnetism, shorted turns, open magnetic circuit)",
    "MID_L": "bulk winding movement or main insulation change",
    "MID":   "winding deformation — axial or radial displacement, disc spacing variation",
    "HIGH":  "lead dressing, grounding, or tap-changer contact",
    "FULL":  "system-wide deviation — investigate measurement setup first",
}


def _format_band_band(per_band: list[BandIndices]) -> dict[str, BandIndices]:
    return {b.band_code: b for b in per_band}


def render_remarks(
    per_band: list[BandIndices],
    full_band: BandIndices,
    band_severity: dict[str, Severity],
    overall: Severity,
    *,
    n_lost: int = 0,
    n_new: int = 0,
    n_shifts: int = 0,
    max_shift_pct: float = 0.0,
) -> str:
    """Generate the auto-remark for a Mode 1 (comparative) result.

    Templates follow spec v2 §7.7 verbatim, with placeholders filled from
    the band/full-band indices. The worst affected band drives the
    root-cause hint.
    """
    by_band = _format_band_band(per_band)

    if overall == Severity.NORMAL:
        cc_low = (by_band.get("LOW", full_band).cc) or 0.0
        cc_mid = (by_band.get("MID", full_band).cc) or 0.0
        cc_high = (by_band.get("HIGH", full_band).cc) or 0.0
        return (
            "Trace within acceptable bounds across all bands "
            f"(CC_LOW={cc_low:.3f}, CC_MID={cc_mid:.3f}, CC_HIGH={cc_high:.3f}). "
            "No significant resonance shifts. Winding and core integrity "
            "consistent with reference."
        )

    # Find the worst band to anchor the remark.
    worst_band_code = "FULL"
    worst_sev = Severity.NORMAL
    for code, sev in band_severity.items():
        if _SEVERITY_RANK.get(sev, 999) < _SEVERITY_RANK.get(worst_sev, 999):
            worst_sev = sev
            worst_band_code = code
    bi = by_band.get(worst_band_code, full_band)

    if overall == Severity.MINOR_DEVIATION:
        return (
            f"Minor deviation in {worst_band_code} band "
            f"(CC={bi.cc or float('nan'):.3f}, RL={bi.rl_factor or float('nan'):.2f}). "
            f"{n_shifts} resonance(s) shifted by up to {max_shift_pct:.1f}%. "
            "Recommend re-test at next routine cycle."
        )

    if overall == Severity.SIGNIFICANT_DEVIATION:
        hint = ROOT_CAUSE_HINTS.get(worst_band_code, ROOT_CAUSE_HINTS["FULL"])
        return (
            f"Significant deviation in {worst_band_code} band suggests {hint}. "
            f"Δmax = {bi.max_dev_db or float('nan'):.1f} dB at "
            f"{bi.max_dev_freq_hz or float('nan'):.0f} Hz. "
            "Recommend internal inspection at earliest scheduled outage."
        )

    if overall == Severity.SEVERE_DEVIATION:
        return (
            f"Severe trace deviation in {worst_band_code} band. "
            f"{n_lost} reference resonance(s) lost, {n_new} new resonance(s) detected. "
            "Do not re-energise without active-part inspection and detailed diagnostic review."
        )

    return f"Overall verdict: {overall.value}. See per-band table for detail."


__all__ = [
    "BandThresholds",
    "ROOT_CAUSE_HINTS",
    "render_remarks",
    "severity_for_rl",
    "worst_severity",
]
