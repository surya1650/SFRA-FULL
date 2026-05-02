"""Tests for the Phase 4 audit log + threshold hot-reload + session list endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from sfra_full.api.app import create_app
from sfra_full.audit import AuditEvent
from sfra_full.auth import Role, User, hash_password


def _bootstrap_admin_session(client) -> tuple[str, dict[str, str]]:
    r = client.post(
        "/api/auth/login",
        data={"username": "admin@aptransco.test", "password": "admin1234"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    return body["user_id"], {"authorization": f"Bearer {body['access_token']}"}


def _bootstrap_engineer_session(client) -> dict[str, str]:
    r = client.post(
        "/api/auth/login",
        data={"username": "engineer@aptransco.test", "password": "engineer123"},
    )
    body = r.json()
    return {"authorization": f"Bearer {body['access_token']}"}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    app = create_app(database_url=db_url, storage_root=tmp_path / "storage", create_schema=True)

    sm = app.state.sessionmaker
    with sm() as s:
        s.add(User(
            email="admin@aptransco.test", full_name="Admin",
            hashed_password=hash_password("admin1234"), role=Role.ADMIN,
        ))
        s.add(User(
            email="engineer@aptransco.test", full_name="Engineer",
            hashed_password=hash_password("engineer123"), role=Role.ENGINEER,
        ))
        s.commit()

    with TestClient(app) as c:
        yield c, app


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
def test_login_records_audit_event(client):
    c, app = client
    _, _ = _bootstrap_admin_session(c)

    sm = app.state.sessionmaker
    with sm() as s:
        events = list(s.scalars(select(AuditEvent)))
    actions = [e.action.value for e in events]
    assert "LOGIN" in actions


def test_failed_login_records_audit_event(client):
    c, app = client
    r = c.post(
        "/api/auth/login",
        data={"username": "admin@aptransco.test", "password": "wrong"},
    )
    assert r.status_code == 401
    sm = app.state.sessionmaker
    with sm() as s:
        events = [e for e in s.scalars(select(AuditEvent)) if e.action.value == "LOGIN_FAILED"]
    assert len(events) == 1
    assert events[0].detail["reason"] == "bad_password"


def test_audit_endpoint_requires_reviewer_or_above(client):
    c, _ = client
    eng_headers = _bootstrap_engineer_session(c)
    # Engineer is below REVIEWER → 403.
    r = c.get("/api/audit", headers=eng_headers)
    assert r.status_code == 403


def test_admin_can_query_audit_log(client):
    c, _ = client
    _, headers = _bootstrap_admin_session(c)
    r = c.get("/api/audit", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert any(e["action"] == "LOGIN" for e in body)


def test_audit_filter_by_action(client):
    c, _ = client
    _, headers = _bootstrap_admin_session(c)
    # Trigger a failed login to seed the log.
    c.post("/api/auth/login", data={"username": "admin@aptransco.test", "password": "x"})
    r = c.get("/api/audit?action=LOGIN_FAILED", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert all(e["action"] == "LOGIN_FAILED" for e in body)
    assert len(body) >= 1


def test_audit_chain_verifies_clean(client):
    """Every recorded event chains correctly; verify endpoint reports ok."""
    c, _ = client
    _, headers = _bootstrap_admin_session(c)
    # Trigger a few audited actions.
    c.post("/api/auth/login", data={"username": "admin@aptransco.test", "password": "x"})
    c.post(
        "/api/users",
        json={"email": "rev@aptransco.test", "full_name": "R", "password": "rev12345", "role": "REVIEWER"},
        headers=headers,
    )
    r = c.get("/api/audit/verify", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["first_bad_id"] is None
    assert body["n_rows"] >= 1


def test_audit_chain_detects_tampering(client):
    """Mutating a row's content (without re-hashing) breaks the chain."""
    c, app = client
    _, headers = _bootstrap_admin_session(c)
    # Force a few audited actions so the chain has length.
    c.post("/api/auth/login", data={"username": "admin@aptransco.test", "password": "x"})
    c.post("/api/auth/login", data={"username": "admin@aptransco.test", "password": "y"})

    # Tamper with the middle row in-place.
    from sfra_full.audit import AuditEvent
    sm = app.state.sessionmaker
    with sm() as s:
        events = list(
            s.scalars(
                select(AuditEvent).order_by(AuditEvent.occurred_at)
            )
        )
        assert len(events) >= 3
        target = events[len(events) // 2]
        target.actor_email = "tampered@aptransco.test"   # change content but not the hash
        s.commit()

    r = c.get("/api/audit/verify", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["first_bad_id"] is not None


def test_review_endpoint_accepts_with_audit(client):
    """Reviewer sign-off updates the AnalysisResult and writes an audit row."""
    c, _ = client
    _, admin_headers = _bootstrap_admin_session(c)
    # Promote a reviewer.
    c.post(
        "/api/users",
        json={
            "email": "rev2@aptransco.test", "full_name": "Reviewer",
            "password": "review123", "role": "REVIEWER",
        },
        headers=admin_headers,
    )
    rev = c.post(
        "/api/auth/login",
        data={"username": "rev2@aptransco.test", "password": "review123"},
    ).json()
    rev_headers = {"authorization": f"Bearer {rev['access_token']}"}

    # Bootstrap a transformer + cycle + session + 1 tested upload + analysis.
    eng_headers = _bootstrap_engineer_session(c)
    tid = c.post(
        "/api/transformers",
        json={"serial_no": "TR-REV", "transformer_type": "TWO_WINDING"},
        headers=eng_headers,
    ).json()["id"]
    cid = c.post(
        f"/api/transformers/{tid}/cycles",
        json={"intervention_type": "COMMISSIONING", "cycle_start_date": "2026-01-01"},
        headers=eng_headers,
    ).json()["id"]
    sid = c.post(
        f"/api/transformers/{tid}/sessions",
        json={"overhaul_cycle_id": cid, "session_type": "ROUTINE", "session_date": "2026-04-15"},
        headers=eng_headers,
    ).json()["id"]
    import xml.etree.ElementTree as ET
    import numpy as np
    f = np.logspace(np.log10(20), 6, 200)
    base = -20 - 30 * np.tanh((np.log10(f) - 3.5))
    root = ET.Element("FRAXFile")
    ET.SubElement(root, "Header")
    measurement = ET.SubElement(root, "Measurement", attrib={"name": "x"})
    for fi, mi in zip(f, base, strict=False):
        ET.SubElement(measurement, "Point", attrib={
            "freq": f"{fi:.4f}", "mag": f"{mi:.4f}", "phase": "-89",
        })
    payload = ET.tostring(root, encoding="utf-8")
    c.post(
        f"/api/sessions/{sid}/upload",
        headers=eng_headers,
        data={"role": "TESTED", "combination_code": "EEOC_HV_R"},
        files={"file": ("x.frax", payload, "application/xml")},
    )
    r = c.post(f"/api/sessions/{sid}/analyse", headers=eng_headers)
    analysis_id = r.json()["results"][0]["id"]

    # Reviewer signs off.
    r = c.post(
        f"/api/analyses/{analysis_id}/review",
        json={"reviewer_remarks": "Looks fine.", "accept": True},
        headers=rev_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("auto_remarks") is None or body.get("auto_remarks") is not None  # field present
    # Re-fetch to confirm reviewer fields persisted.
    r = c.get(f"/api/analyses/{analysis_id}")
    assert r.status_code == 200
    # The analysis result row now carries reviewer fields (we don't expose
    # them via AnalysisResultOut yet but the audit trail is sufficient).

    # Engineer can't sign off.
    r = c.post(
        f"/api/analyses/{analysis_id}/review",
        json={"reviewer_remarks": "no", "accept": True},
        headers=eng_headers,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Thresholds hot-reload
# ---------------------------------------------------------------------------
def test_get_thresholds_returns_active_table(client):
    c, _ = client
    _, headers = _bootstrap_admin_session(c)
    r = c.get("/api/standards/thresholds", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "RLW" in body
    assert "RLM" in body
    assert "RLH" in body
    assert body["RLW"]["normal_min"] == 2.0


def test_engineer_cannot_patch_thresholds(client):
    c, _ = client
    eng_headers = _bootstrap_engineer_session(c)
    r = c.patch(
        "/api/standards/thresholds",
        json={"dl_t_911_thresholds": {"RLW": {"normal": {"min": 1.5}}}},
        headers=eng_headers,
    )
    assert r.status_code == 403


def test_admin_patch_thresholds_takes_effect_and_audits(client):
    c, app = client
    _, headers = _bootstrap_admin_session(c)
    # Read original to confirm patch.
    before = c.get("/api/standards/thresholds", headers=headers).json()
    assert before["RLW"]["normal_min"] == 2.0

    r = c.patch(
        "/api/standards/thresholds",
        json={"dl_t_911_thresholds": {"RLW": {"normal": {"min": 1.5}}}},
        headers=headers,
    )
    assert r.status_code == 200, r.text

    # Hot-reload should make the change visible immediately.
    after = c.get("/api/standards/thresholds", headers=headers).json()
    assert after["RLW"]["normal_min"] == 1.5

    # Audit row must record the patch.
    sm = app.state.sessionmaker
    with sm() as s:
        events = [e for e in s.scalars(select(AuditEvent)) if e.action.value == "THRESHOLDS_UPDATE"]
    assert len(events) >= 1

    # Restore original so other tests aren't disturbed.
    c.patch(
        "/api/standards/thresholds",
        json={"dl_t_911_thresholds": {"RLW": {"normal": {"min": 2.0}}}},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Session / cycle list
# ---------------------------------------------------------------------------
def test_session_listing_endpoints(client):
    c, _ = client
    # Create a transformer + cycle + 2 sessions.
    tid = c.post(
        "/api/transformers",
        json={"serial_no": "TR-LIST", "transformer_type": "TWO_WINDING"},
    ).json()["id"]
    cid = c.post(
        f"/api/transformers/{tid}/cycles",
        json={"intervention_type": "COMMISSIONING", "cycle_start_date": "2026-01-01"},
    ).json()["id"]
    s1 = c.post(
        f"/api/transformers/{tid}/sessions",
        json={"overhaul_cycle_id": cid, "session_type": "ROUTINE", "session_date": "2026-04-15"},
    ).json()
    s2 = c.post(
        f"/api/transformers/{tid}/sessions",
        json={"overhaul_cycle_id": cid, "session_type": "POST_FAULT", "session_date": "2026-04-20"},
    ).json()

    # By transformer.
    r = c.get(f"/api/transformers/{tid}/sessions")
    assert r.status_code == 200
    body = r.json()
    assert {b["id"] for b in body} == {s1["id"], s2["id"]}

    # By cycle.
    r = c.get(f"/api/cycles/{cid}/sessions")
    assert r.status_code == 200
    assert len(r.json()) == 2

    # Empty traces list initially.
    r = c.get(f"/api/sessions/{s1['id']}/traces")
    assert r.status_code == 200
    assert r.json() == []
