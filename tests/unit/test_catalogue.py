"""Test the IEEE C57.149 combination catalogue YAML."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def test_validator_passes() -> None:
    """The validator script must exit 0 on the committed catalogue."""
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["python3", str(repo / "scripts" / "validate_catalogue.py")],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Catalogue validator failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
    assert "OK" in result.stdout


@pytest.mark.parametrize(
    "ttype,expected_count",
    [
        ("TWO_WINDING", 15),
        ("AUTO_WITH_TERTIARY_BROUGHT_OUT", 21),
        ("AUTO_WITH_TERTIARY_BURIED", 12),
        ("THREE_WINDING", 36),
    ],
)
def test_combination_count(ttype: str, expected_count: int) -> None:
    """Spec v2 §5: each transformer type must expose the documented row count."""
    import yaml
    repo = Path(__file__).resolve().parents[2]
    data = yaml.safe_load(
        (repo / "standards" / "ieee_c57_149_combinations.yaml").read_text()
    )
    rows = data["transformer_types"][ttype]["combinations"]
    assert len(rows) == expected_count


def test_three_winding_complete_set() -> None:
    """Spec v2 §5.4: THREE_WINDING covers all 36 EEOC/EESC/CIW/IIW combos."""
    import yaml
    repo = Path(__file__).resolve().parents[2]
    data = yaml.safe_load(
        (repo / "standards" / "ieee_c57_149_combinations.yaml").read_text()
    )
    rows = data["transformer_types"]["THREE_WINDING"]["combinations"]
    cats = {r["category"] for r in rows}
    # All 4 EESC + EEOC + CIW + IIW family categories must be present.
    assert "EEOC_HV" in cats
    assert "EEOC_IV" in cats
    assert "EEOC_LV" in cats
    assert "EESC_HV" in cats
    assert "EESC_IV" in cats
    assert "CIW_HV_IV" in cats
    assert "CIW_HV_LV" in cats
    assert "CIW_IV_LV" in cats
    assert "IIW_HV_IV" in cats
    assert "IIW_HV_LV" in cats
    assert "IIW_IV_LV" in cats
    # 9 EEOC + 6 EESC default + 3 EESC_LVS + 9 CIW + 9 IIW = 36
    eeoc = [r for r in rows if r["category"].startswith("EEOC_")]
    eesc = [r for r in rows if r["category"].startswith("EESC_")]
    ciw = [r for r in rows if r["category"].startswith("CIW_")]
    iiw = [r for r in rows if r["category"].startswith("IIW_")]
    assert len(eeoc) == 9
    assert len(eesc) == 9
    assert len(ciw) == 9
    assert len(iiw) == 9
