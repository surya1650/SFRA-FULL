#!/usr/bin/env python3
"""Validate ``standards/ieee_c57_149_combinations.yaml`` against spec v2.

Spec v2 §5 enumerates the combination catalogue per transformer type.
Catching a wrong row count at this layer guards every downstream consumer
(UI dropdowns, FRAX importer, report tables) from agreeing on a wrong
count — and protects the §6.2 "single-combination upload must always
work" invariant by ensuring every code in the catalogue is well-formed.

Run via ``make validate-catalogue`` or as a pre-commit hook.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOGUE = ROOT / "standards" / "ieee_c57_149_combinations.yaml"

# Per spec v2 §5 (IEEE C57.149-2012 Table 1, condensed for APTRANSCO fleet).
# THREE_WINDING is intentionally pending — spec v2 lists it in the
# transformer_type enum but does not enumerate the combination set; that
# enumeration is part of Phase 1 engineering review.
EXPECTED_COUNTS: dict[str, int | None] = {
    "TWO_WINDING": 15,
    "AUTO_WITH_TERTIARY_BROUGHT_OUT": 21,
    "AUTO_WITH_TERTIARY_BURIED": 12,
    "THREE_WINDING": None,  # pending engineering enumeration
}

REQUIRED_ROW_KEYS = {
    "sequence",
    "code",
    "category",
    "winding",
    "phase",
    "injection_terminal",
    "measurement_terminal",
    "shorted_terminals",
    "grounded_terminals",
    "description",
}

# Allowed Combination.category enum values per spec v2 §3 DB schema.
ALLOWED_CATEGORIES = {
    "EEOC_HV", "EEOC_LV", "EEOC_TV", "EEOC_IV",
    "EESC_HV", "EESC_LV", "EESC_IV",
    "CIW_HV_LV", "CIW_HV_TV", "CIW_HV_IV", "CIW_LV_TV", "CIW_IV_TV",
    "IIW_HV_LV", "IIW_HV_TV", "IIW_HV_IV", "IIW_LV_TV", "IIW_IV_TV",
}

# Codes follow the FRAX resolver pattern from spec v2 §4.1.
# Examples: EEOC_HV_R, EESC_HV_R_TVS, CIW_HV_TV_S, IIW_HV_LV_T.
CODE_PATTERN = re.compile(
    r"^(EEOC|EESC|CIW|IIW)_(HV|LV|TV|IV)(?:_(HV|LV|TV|IV))?_[RST](?:_TVS|_LVS|_HVS|_IVS)?$"
)

ALLOWED_PHASES = {"R", "S", "T"}


def _fail(msg: str) -> None:
    print(f"[validate-catalogue] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if not CATALOGUE.exists():
        _fail(f"catalogue not found: {CATALOGUE}")

    data = yaml.safe_load(CATALOGUE.read_text(encoding="utf-8"))

    types = data.get("transformer_types", {})
    if set(types.keys()) != set(EXPECTED_COUNTS.keys()):
        _fail(
            "transformer_types keys mismatch.\n"
            f"  expected: {sorted(EXPECTED_COUNTS)}\n"
            f"  found:    {sorted(types.keys())}"
        )

    errors: list[str] = []
    total_rows = 0
    for ttype, expected in EXPECTED_COUNTS.items():
        spec = types[ttype]
        rows = spec.get("combinations", []) or []

        if expected is None:
            # THREE_WINDING — must be marked pending.
            if not spec.get("pending_enumeration"):
                errors.append(
                    f"{ttype}: count not yet set; must declare 'pending_enumeration: true'"
                )
            if rows:
                errors.append(
                    f"{ttype}: pending_enumeration but combinations list is non-empty "
                    f"({len(rows)} rows). Empty the list or remove the pending flag."
                )
            continue

        if spec.get("total") != expected:
            errors.append(f"{ttype}: total={spec.get('total')} (expected {expected})")
        if len(rows) != expected:
            errors.append(
                f"{ttype}: combinations list has {len(rows)} rows (expected {expected})"
            )

        seen_sequences: set[int] = set()
        seen_codes: set[str] = set()
        for row in rows:
            code = row.get("code", "?")
            missing = REQUIRED_ROW_KEYS - row.keys()
            if missing:
                errors.append(f"{ttype}/{code}: missing keys {sorted(missing)}")

            cat = row.get("category")
            if cat not in ALLOWED_CATEGORIES:
                errors.append(f"{ttype}/{code}: bad category '{cat}'")

            phase = row.get("phase")
            if phase not in ALLOWED_PHASES:
                errors.append(f"{ttype}/{code}: bad phase '{phase}' (must be R/S/T)")

            if isinstance(code, str):
                if not CODE_PATTERN.match(code):
                    errors.append(
                        f"{ttype}/{code}: code does not match pattern "
                        f"(expect e.g. EEOC_HV_R or EESC_HV_R_TVS)"
                    )
                if code in seen_codes:
                    errors.append(f"{ttype}: duplicate code '{code}'")
                seen_codes.add(code)

            seq = row.get("sequence")
            if not isinstance(seq, int):
                errors.append(f"{ttype}/{code}: non-integer sequence")
            else:
                seen_sequences.add(seq)

        # Sequence numbers must be 1..N contiguous.
        if seen_sequences != set(range(1, expected + 1)):
            missing_seq = set(range(1, expected + 1)) - seen_sequences
            extra_seq = seen_sequences - set(range(1, expected + 1))
            if missing_seq:
                errors.append(f"{ttype}: missing sequence numbers {sorted(missing_seq)}")
            if extra_seq:
                errors.append(f"{ttype}: unexpected sequence numbers {sorted(extra_seq)}")

        total_rows += len(rows)

    if errors:
        for e in errors:
            print(f"[validate-catalogue] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Spec v2 §5 totals: 15 + 21 + 12 + (TBD) = 48 (+ THREE_WINDING)
    print(
        f"[validate-catalogue] OK: 4 transformer types, {total_rows} combinations enumerated "
        "(15 + 21 + 12 = 48; THREE_WINDING pending Phase 1 engineering review)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
