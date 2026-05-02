"""Auth tests — JWT issue/verify + role gating."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sfra_full.api.app import create_app
from sfra_full.auth import Role, User, hash_password


@pytest.fixture()
def client_and_session(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    app = create_app(
        database_url=db_url, storage_root=tmp_path / "storage", create_schema=True
    )
    sm = app.state.sessionmaker
    with sm() as s:
        s.add(
            User(
                email="engineer@aptransco.test",
                full_name="Engineer A",
                hashed_password=hash_password("engineer123"),
                role=Role.ENGINEER,
            )
        )
        s.add(
            User(
                email="admin@aptransco.test",
                full_name="Admin B",
                hashed_password=hash_password("admin1234"),
                role=Role.ADMIN,
            )
        )
        s.commit()
    with TestClient(app) as c:
        yield c


def test_login_issues_token_and_me_returns_user(client_and_session):
    c = client_and_session
    r = c.post(
        "/api/auth/login",
        data={"username": "engineer@aptransco.test", "password": "engineer123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "ENGINEER"
    token = body["access_token"]

    r = c.get("/api/auth/me", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == "engineer@aptransco.test"
    assert me["role"] == "ENGINEER"


def test_login_with_bad_password_rejected(client_and_session):
    c = client_and_session
    r = c.post(
        "/api/auth/login",
        data={"username": "engineer@aptransco.test", "password": "wrong"},
    )
    assert r.status_code == 401


def test_admin_endpoint_blocks_engineer(client_and_session):
    c = client_and_session
    eng = c.post(
        "/api/auth/login",
        data={"username": "engineer@aptransco.test", "password": "engineer123"},
    ).json()
    r = c.get(
        "/api/users",
        headers={"authorization": f"Bearer {eng['access_token']}"},
    )
    assert r.status_code == 403  # Engineer can't list users


def test_admin_can_create_and_list_users(client_and_session):
    c = client_and_session
    admin = c.post(
        "/api/auth/login",
        data={"username": "admin@aptransco.test", "password": "admin1234"},
    ).json()
    headers = {"authorization": f"Bearer {admin['access_token']}"}
    r = c.post(
        "/api/users",
        json={
            "email": "reviewer@aptransco.test",
            "full_name": "Reviewer C",
            "password": "reviewer1",
            "role": "REVIEWER",
        },
        headers=headers,
    )
    assert r.status_code == 201
    r = c.get("/api/users", headers=headers)
    assert r.status_code == 200
    assert any(u["email"] == "reviewer@aptransco.test" for u in r.json())


def test_missing_authorization_returns_401(client_and_session):
    r = client_and_session.get("/api/auth/me")
    assert r.status_code == 401


def test_sso_endpoints_return_501(client_and_session):
    r = client_and_session.get("/api/auth/sso/login")
    assert r.status_code == 501
