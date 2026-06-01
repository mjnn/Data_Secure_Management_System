"""认证令牌轮换、吊销与权限相关测试。"""

import uuid

import pytest


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_refresh_token_rotation_and_reuse_blocked(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    old_refresh = r.json()["refresh_token"]

    r = api_client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200, r.text
    new_refresh = r.json()["refresh_token"]
    assert new_refresh != old_refresh

    r = api_client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 401


def test_logout_revokes_refresh_token(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    refresh = r.json()["refresh_token"]

    r = api_client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert r.status_code == 204

    r = api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


def test_password_change_invalidates_refresh_tokens(api_client):
    from app.core.config import settings
    from app.core.security import get_password_hash
    from app.core.database import engine
    from app.models import User
    from sqlmodel import Session, select

    username = f"pytest-pwd-{uuid.uuid4().hex[:8]}"
    old_password = "TempPwd123456"
    new_password = "TempPwd654321"

    with Session(engine) as session:
        user = User(
            username=username,
            email=f"{username}@local.dsms",
            hashed_password=get_password_hash(old_password),
            is_active=True,
            is_approved=True,
        )
        session.add(user)
        session.commit()

    r = api_client.post("/api/v1/auth/login", json={"username": username, "password": old_password})
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]
    refresh = r.json()["refresh_token"]

    r = api_client.post(
        "/api/v1/users/me/password",
        json={"old_password": old_password, "new_password": new_password},
        headers=_auth(access),
    )
    assert r.status_code == 204, r.text

    r = api_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


def test_function_fo_cannot_approve_submission_task(api_client):
    from app.core.config import settings

    admin = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert admin.status_code == 200, admin.text
    admin_h = _auth(admin.json()["access_token"])

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 1}, headers=admin_h)
    tenant_id = r.json()["items"][0]["id"]
    r = api_client.get(f"/api/v1/dsms/tenants/{tenant_id}/spaces", params={"skip": 0, "limit": 1}, headers=admin_h)
    space_id = r.json()["items"][0]["id"]
    base = f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}"

    r = api_client.post(
        f"{base}/submission-tasks",
        json={"function_key": "field_usage", "title": f"pytest-authz-{uuid.uuid4().hex[:6]}", "internal_note": ""},
        headers=admin_h,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]

    fo = api_client.post(
        "/api/v1/auth/login",
        json={"username": "function_fo", "password": settings.test_function_fo_password},
    )
    assert fo.status_code == 200, fo.text
    fo_h = _auth(fo.json()["access_token"])

    r = api_client.patch(
        f"{base}/submission-tasks/{task_id}",
        json={"fields": {"auditStatus": "approved", "auditComment": "越权尝试"}},
        headers=fo_h,
    )
    assert r.status_code == 403


def test_security_headers_present(api_client):
    r = api_client.get("/healthz")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
