"""空间归属校验：跨 tenant 的 space_id 应返回 404。"""

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


def test_create_field_catalog_rejects_foreign_space(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 5}, headers=h)
    tenants = r.json()["items"]
    assert len(tenants) >= 1
    tenant_a = tenants[0]["id"]

    slug = f"pytest-space-check-{uuid.uuid4().hex[:8]}"
    r = api_client.post("/api/v1/dsms/tenants", json={"name": "pytest 空间校验", "slug": slug}, headers=h)
    assert r.status_code == 200, r.text
    tenant_b = r.json()["id"]

    r = api_client.get(f"/api/v1/dsms/tenants/{tenant_a}/spaces", params={"skip": 0, "limit": 1}, headers=h)
    space_a = r.json()["items"][0]["id"]

    r = api_client.post(
        f"/api/v1/dsms/tenants/{tenant_b}/spaces/{space_a}/field-catalog",
        json={
            "field_name": f"pytest_{uuid.uuid4().hex[:6]}",
            "identifier_key": f"pytest_{uuid.uuid4().hex[:6]}",
            "data_type": "string",
        },
        headers=h,
    )
    assert r.status_code == 404
