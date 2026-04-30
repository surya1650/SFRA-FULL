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


def test_three_winding_pending() -> None:
    """THREE_WINDING is intentionally pending engineering enumeration."""
    import yaml
    repo = Path(__file__).resolve().parents[2]
    data = yaml.safe_load(
        (repo / "standards" / "ieee_c57_149_combinations.yaml").read_text()
    )
    spec = data["transformer_types"]["THREE_WINDING"]
    assert spec.get("pending_enumeration") is True
    assert spec.get("combinations", []) == []
