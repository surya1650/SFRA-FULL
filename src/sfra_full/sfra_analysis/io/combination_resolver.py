"""FRAX <Property> dict → spec v2 §5 combination_code resolver.

Spec v2 §4.1 gives the canonical mapping. This module is the single source
of truth for that translation; the FRAX parser, the CSV parser (when the
user supplies properties manually), and the API combination assignment
endpoint all call ``resolve_combination_code``.

If a sweep doesn't map to any seeded combination — common with placeholder
rows in real FRAX exports — the resolver returns ``None`` and the parser
attaches the sweep with ``combination_id = NULL`` so the UI can prompt
the engineer to assign it manually (per spec v2 §4.1 last paragraph).
"""
from __future__ import annotations

from typing import Any, Optional

# Phase code map: FRAX uses R/S/T (red/yellow/blue), spec v2 expects R/S/T.
_PHASE_MAP: dict[str, str] = {
    "R": "R", "S": "S", "T": "T",
    # Some FRAX firmwares emit 1U/1V/1W instead of R/S/T — translate.
    "1U": "R", "1V": "S", "1W": "T",
    "U": "R", "V": "S", "W": "T",
    # Defensive aliases
    "A": "R", "B": "S", "C": "T",
}

_WINDING_MAP: dict[str, str] = {
    "HV": "HV", "LV": "LV", "TV": "TV", "IV": "IV",
    # Aliases sometimes used by FRAX firmware
    "Primary": "HV", "Secondary": "LV", "Tertiary": "TV",
    "1": "HV", "2": "LV", "3": "TV",
}


def _norm(val: Optional[str]) -> str:
    if val is None:
        return ""
    return str(val).strip().upper()


def _phase(p: Optional[str]) -> Optional[str]:
    return _PHASE_MAP.get(_norm(p))


def _winding(w: Optional[str]) -> Optional[str]:
    return _WINDING_MAP.get(_norm(w)) or (
        _norm(w) if _norm(w) in {"HV", "LV", "TV", "IV"} else None
    )


def _shorted_class(shorted: Optional[str]) -> Optional[str]:
    """Classify the 'Shorted terminals' string as 'LV', 'TV', or None.

    Spec v2 §4.1 rule: terminals starting with '2' indicate LV/IV
    shorted; '3' indicates TV (tertiary) shorted. '1' would mean HV
    shorted (rare — indicates a cross-short variant).
    """
    s = _norm(shorted)
    if not s:
        return None
    # FRAX uses dash-separated terminal lists, e.g. "2U-2V-2W".
    first = s.split("-")[0].strip()
    if not first:
        return None
    if first.startswith("3"):
        return "TV"
    if first.startswith("2"):
        return "LV"
    if first.startswith("1"):
        return "HV"
    return None


def resolve_combination_code(properties: dict[str, Any]) -> Optional[str]:
    """Translate a FRAX <Properties> dict into a spec v2 §5 combination code.

    Returns ``None`` when the sweep is a placeholder (no Test type) or
    cannot be unambiguously resolved.
    """
    test = _norm(properties.get("Test"))
    if not test:
        return None

    open_short = _norm(properties.get("OpenShort"))
    phase = _phase(properties.get("Phase"))
    winding = _winding(properties.get("Winding"))
    shorted_klass = _shorted_class(properties.get("Shorted terminals"))

    if test == "END-TO-END":
        if not phase or not winding:
            return None

        if open_short == "OPEN":
            return f"EEOC_{winding}_{phase}"

        if open_short == "SHORT":
            base = f"EESC_{winding}_{phase}"
            if shorted_klass == "TV":
                return f"{base}_TVS"
            if shorted_klass == "HV":
                return f"{base}_HVS"
            # Default: LV/IV shorted — spec v2 default suffix-less form.
            return base
        return None

    if test in ("CAPACITIVE INTERWINDING", "CAPACITIVE INTER-WINDING", "CAPACITIVE"):
        if not phase or not winding:
            return None
        # Pair winding (where the response is measured)
        meas_w = _winding(properties.get("Response winding")) \
            or _winding(properties.get("Response terminal"))
        if not meas_w:
            # Heuristic from terminal numbers.
            resp = _norm(properties.get("Response terminal"))
            if resp.startswith("2"):
                meas_w = "LV"
            elif resp.startswith("3"):
                meas_w = "TV"
        if not meas_w:
            return None
        return f"CIW_{winding}_{meas_w}_{phase}"

    if test in ("INDUCTIVE INTERWINDING", "INDUCTIVE INTER-WINDING", "INDUCTIVE"):
        if not phase or not winding:
            return None
        meas_w = _winding(properties.get("Response winding")) \
            or _winding(properties.get("Response terminal"))
        if not meas_w:
            resp = _norm(properties.get("Response terminal"))
            if resp.startswith("2"):
                meas_w = "LV"
            elif resp.startswith("3"):
                meas_w = "TV"
        if not meas_w:
            return None
        return f"IIW_{winding}_{meas_w}_{phase}"

    return None


__all__ = ["resolve_combination_code"]
