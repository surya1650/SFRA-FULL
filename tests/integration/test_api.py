"""End-to-end API tests — covers the full §6 flow including spec v2 §6.2.

Single-trace upload + analyse path (Mode 2):
    1. POST /api/transformers
    2. POST /api/transformers/{id}/cycles
    3. POST /api/transformers/{id}/sessions
    4. POST /api/sessions/{id}/upload   (tested trace, no reference yet)
    5. POST /api/sessions/{id}/analyse  → mode_2_count == 1

When a reference is uploaded later, re-running /analyse switches that
combination's row to Mode 1 — invariant verified at the bottom.
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from datetime import date

import numpy as np
import pytest
from fastapi.testclient import TestClient

from sfra_full.api.app import create_app


def _synth_frax(label: str, n: int = 200, shift: float = 0.0) -> bytes:
    """Build a FRAX_LEGACY XML payload the parser will read."""
    root = ET.Element("FRAXFile")
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "Transformer").text = "TR-T1"
    measurement = ET.SubElement(root, "Measurement", attrib={"name": label})
    f = np.logspace(np.log10(20), 6, n)
    base = -20 - 30 * np.tanh((np.log10(f) - 3.5) / 1.0)
    res = np.zeros_like(f)
    for fc, depth, q in [(12_300, 18, 12), (85_000, 14, 10), (340_000, 10, 8)]:
        fc *= 1 + shift
        res -= depth / (1.0 + ((np.log10(f) - np.log10(fc)) * q) ** 2)
    mag = base + res
    phase = -90 + 40 * np.tanh((np.log10(f) - 4.0) / 1.0)
    for fi, mi, pi in zip(f, mag, phase, strict=False):
        ET.SubElement(measurement, "Point", attrib={
            "freq": f"{fi:.4f}",
            "mag": f"{mi:.4f}",
            "phase": f"{pi:.4f}",
        })
    return ET.tostring(root, encoding="utf-8")


@pytest.fixture()
def client(tmp_path):
    # File-based SQLite so all FastAPI request connections see the same
    # schema — `:memory:` resets per connection.
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    app = create_app(
        database_url=db_url,
        storage_root=tmp_path / "storage",
        create_schema=True,
    )
    # Seed the combination table so combination_code → combination_id binding
    # works in the upload + analyse flow. Without this, reference/tested
    # traces would all have combination_id=NULL and the runner could not
    # pair them in the same overhaul cycle.
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parents[2] / "scripts"))
    import seed_combinations  # type: ignore[import-not-found]
    seed_combinations.seed(db_url)

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_standards_combinations_yaml_fallback(client):
    """Without seeding, the endpoint falls back to YAML."""
    r = client.get("/api/standards/combinations?transformer_type=TWO_WINDING")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 15
    codes = {row["code"] for row in rows}
    assert "EEOC_HV_R" in codes
    assert "IIW_HV_LV_T" in codes


def test_transformer_crud(client):
    r = client.post(
        "/api/transformers",
        json={
            "serial_no": "TR-INT-1",
            "transformer_type": "TWO_WINDING",
            "nameplate_mva": 100.0,
        },
    )
    assert r.status_code == 201
    tid = r.json()["id"]

    r = client.post(
        "/api/transformers",
        json={"serial_no": "TR-INT-1", "transformer_type": "TWO_WINDING"},
    )
    assert r.status_code == 409  # duplicate serial

    r = client.get(f"/api/transformers/{tid}")
    assert r.status_code == 200
    assert r.json()["serial_no"] == "TR-INT-1"


def test_cycle_close_on_new_open(client):
    r = client.post(
        "/api/transformers",
        json={"serial_no": "TR-CYC", "transformer_type": "TWO_WINDING"},
    ).json()
    tid = r["id"]

    r1 = client.post(
        f"/api/transformers/{tid}/cycles",
        json={
            "intervention_type": "COMMISSIONING",
            "cycle_start_date": "2026-01-01",
        },
    )
    assert r1.status_code == 201
    assert r1.json()["cycle_no"] == 1
    assert r1.json()["is_open"] is True

    r2 = client.post(
        f"/api/transformers/{tid}/cycles",
        json={
            "intervention_type": "MAJOR_OVERHAUL",
            "cycle_start_date": "2030-06-01",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["cycle_no"] == 2

    cycles = client.get(f"/api/transformers/{tid}/cycles").json()
    assert len(cycles) == 2
    # Cycle 1 closed when cycle 2 opened.
    assert cycles[0]["cycle_end_date"] == "2030-06-01"
    assert cycles[0]["is_open"] is False
    assert cycles[1]["is_open"] is True


def _make_transformer_with_session(client, serial: str = "TR-FLOW"):
    tid = client.post(
        "/api/transformers",
        json={"serial_no": serial, "transformer_type": "TWO_WINDING"},
    ).json()["id"]
    cid = client.post(
        f"/api/transformers/{tid}/cycles",
        json={"intervention_type": "COMMISSIONING", "cycle_start_date": "2026-01-01"},
    ).json()["id"]
    sid = client.post(
        f"/api/transformers/{tid}/sessions",
        json={
            "overhaul_cycle_id": cid,
            "session_type": "ROUTINE",
            "session_date": "2026-04-15",
        },
    ).json()["id"]
    return tid, cid, sid


def test_upload_single_trace_mode2_then_reference_promotes_to_mode1(client):
    """Spec v2 §6.2: tested-only upload → Mode 2; reference arrival → Mode 1."""
    tid, cid, sid = _make_transformer_with_session(client)

    # Upload a tested trace ONLY.
    payload = _synth_frax("HV-A end-to-end", shift=0.04)
    r = client.post(
        f"/api/sessions/{sid}/upload",
        data={"role": "TESTED", "combination_code": "EEOC_HV_R"},
        files={"file": ("test.frax", payload, "application/xml")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["n_traces_persisted"] == 1
    assert body["traces"][0]["source_file_sha256"]

    # Run analysis — no reference exists yet → Mode 2.
    r = client.post(f"/api/sessions/{sid}/analyse")
    assert r.status_code == 200
    out = r.json()
    assert out["n_results"] == 1
    assert out["mode_2_count"] == 1
    assert out["mode_1_count"] == 0
    assert out["results"][0]["mode"] == "reference_missing_analysis"
    assert out["results"][0]["severity"] in {"APPEARS_NORMAL", "SUSPECT", "INDETERMINATE"}

    # Now upload the matching reference trace into the SAME open cycle's
    # session — for Phase 1 we attach it to the same session.
    ref_payload = _synth_frax("HV-A end-to-end (ref)", shift=0.0)
    r = client.post(
        f"/api/sessions/{sid}/upload",
        data={"role": "REFERENCE", "combination_code": "EEOC_HV_R"},
        files={"file": ("ref.frax", ref_payload, "application/xml")},
    )
    assert r.status_code == 201

    # Re-run analysis → the same tested trace now hits Mode 1.
    r = client.post(f"/api/sessions/{sid}/analyse")
    assert r.status_code == 200
    out = r.json()
    assert out["mode_1_count"] == 1
    assert out["mode_2_count"] == 0
    assert out["results"][0]["mode"] == "comparative"


def test_upload_unmapped_combination_surfaces_in_response(client):
    """A FRAX without a resolvable combination_code is reported, not failed."""
    tid, cid, sid = _make_transformer_with_session(client, serial="TR-UNMAP")
    payload = _synth_frax("unknown-sweep")
    # No combination_code form param AND the synthetic XML has no <Properties>,
    # so the resolver returns None.
    r = client.post(
        f"/api/sessions/{sid}/upload",
        data={"role": "TESTED"},
        files={"file": ("unknown.frax", payload, "application/xml")},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["n_sweeps_parsed"] == 1
    # Persisted but unmapped — combination_id is null.
    assert body["traces"][0]["combination_id"] is None
    assert body["unmapped_sweeps"][0]["sweep_index"] == 0


def test_get_trace_data_returns_decoded_arrays(client):
    tid, cid, sid = _make_transformer_with_session(client, serial="TR-DECODE")
    payload = _synth_frax("HV-A end-to-end")
    upload = client.post(
        f"/api/sessions/{sid}/upload",
        data={"role": "TESTED", "combination_code": "EEOC_HV_R"},
        files={"file": ("trace.frax", payload, "application/xml")},
    ).json()
    trace_id = upload["traces"][0]["id"]

    r = client.get(f"/api/traces/{trace_id}/data")
    assert r.status_code == 200
    body = r.json()
    assert body["point_count"] == 200
    assert len(body["frequency_hz"]) == 200
    assert len(body["magnitude_db"]) == 200
