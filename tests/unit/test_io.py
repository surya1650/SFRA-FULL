"""Tests for sfra_analysis.io combination resolver and parsers."""
from __future__ import annotations

from sfra_full.sfra_analysis.io.combination_resolver import resolve_combination_code


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------
def test_eeoc_hv_phase_r() -> None:
    props = {"Test": "End-to-end", "OpenShort": "Open", "Phase": "R", "Winding": "HV"}
    assert resolve_combination_code(props) == "EEOC_HV_R"


def test_eesc_hv_lv_shorted() -> None:
    """Default short (LV winding shorted) → no suffix."""
    props = {
        "Test": "End-to-end", "OpenShort": "Short",
        "Phase": "S", "Winding": "HV",
        "Shorted terminals": "2U-2V-2W",
    }
    assert resolve_combination_code(props) == "EESC_HV_S"


def test_eesc_hv_tertiary_shorted_gets_tvs_suffix() -> None:
    props = {
        "Test": "End-to-end", "OpenShort": "Short",
        "Phase": "T", "Winding": "HV",
        "Shorted terminals": "3U-3V-3W",
    }
    assert resolve_combination_code(props) == "EESC_HV_T_TVS"


def test_ciw_hv_lv() -> None:
    props = {
        "Test": "Capacitive interwinding",
        "Phase": "R", "Winding": "HV",
        "Response winding": "LV",
    }
    assert resolve_combination_code(props) == "CIW_HV_LV_R"


def test_iiw_hv_tv_via_response_terminal_inference() -> None:
    """Response winding inferred from terminal numbering when missing."""
    props = {
        "Test": "Inductive interwinding",
        "Phase": "S", "Winding": "HV",
        "Response terminal": "3V",
    }
    assert resolve_combination_code(props) == "IIW_HV_TV_S"


def test_placeholder_returns_none() -> None:
    """Empty Properties → unrecognised → None (spec v2 §4.1)."""
    assert resolve_combination_code({}) is None
    assert resolve_combination_code({"OpenShort": "Open"}) is None


def test_phase_alias_mapping() -> None:
    """Some FRAX firmwares emit U/V/W instead of R/S/T."""
    props = {"Test": "End-to-end", "OpenShort": "Open", "Phase": "U", "Winding": "HV"}
    assert resolve_combination_code(props) == "EEOC_HV_R"
    props["Phase"] = "1V"
    assert resolve_combination_code(props) == "EEOC_HV_S"


# ---------------------------------------------------------------------------
# CSV parser smoke
# ---------------------------------------------------------------------------
def test_parse_csv_roundtrip(tmp_path) -> None:
    """CSV with Hz + dB + degrees parses cleanly."""
    from sfra_full.sfra_analysis.io.csv import parse_csv

    p = tmp_path / "synthetic.csv"
    p.write_text(
        "frequency_hz,magnitude_db,phase_deg\n"
        "100,-20.5,-89.0\n"
        "1000,-25.1,-87.2\n"
        "10000,-30.3,-80.0\n"
        "100000,-35.7,-65.0\n",
        encoding="utf-8",
    )
    sweeps = parse_csv(str(p))
    assert len(sweeps) == 1
    s = sweeps[0]
    assert s.source_format == "CSV"
    assert s.frequency_hz.size == 4
    assert s.magnitude_db[0] == -20.5
    assert s.phase_deg is not None


def test_dispatch_detects_xml_as_frax() -> None:
    """Dispatch routes XML payloads to the FRAX parser."""
    from sfra_full.sfra_analysis.io import parse_file

    xml = (
        "<FRAXFile><Header><Transformer>X</Transformer></Header>"
        "<Measurement name='HV-A'>"
        "<Point freq='100' mag='-20' phase='-89'/>"
        "<Point freq='1000' mag='-25' phase='-87'/>"
        "<Point freq='10000' mag='-30' phase='-80'/>"
        "</Measurement></FRAXFile>"
    )
    fmt, sweeps = parse_file(xml.encode("utf-8"), source_filename="x.frax")
    assert fmt == "FRAX"
    assert len(sweeps) == 1
    assert sweeps[0].frequency_hz.size == 3
