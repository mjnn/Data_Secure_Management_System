"""JWT + 项目/空间 + Phase2 矩阵的端到端冒烟（依赖 conftest 中的 DATABASE_URL）。"""

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


def test_login_tenant_space_classification_matrix(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    token = body["access_token"]

    slug = f"pytest-{uuid.uuid4().hex[:12]}"
    r = api_client.post(
        "/api/v1/dsms/tenants",
        json={"name": "pytest 项目", "slug": slug},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    tenant_id = r.json()["id"]

    sk = f"sp_{uuid.uuid4().hex[:8]}"
    r = api_client.post(
        f"/api/v1/dsms/tenants/{tenant_id}/spaces",
        json={"space_key": sk, "name": "pytest 空间"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    space_id = r.json()["id"]

    r = api_client.get(
        f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}/classification/matrix",
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    lst = r.json()
    assert lst["total"] == 0

    r = api_client.post(
        f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}/classification/matrix",
        json={"name": "pytest矩阵", "description": "", "cells_json": "[]"},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text

    r = api_client.get(
        f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}/classification/matrix",
        headers=_auth(token),
    )
    assert r.json()["total"] >= 1
