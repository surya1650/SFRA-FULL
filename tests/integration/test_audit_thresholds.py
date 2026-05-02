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
