"""门户核心 API 联调冒烟（任务 / 问卷 / 生命周期 / 审批）。"""

import json
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


def test_portal_submission_and_config_flow(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    h = _auth(token)

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 20}, headers=h)
    assert r.status_code == 200, r.text
    tenant = r.json()["items"][0]
    tenant_id = tenant["id"]

    r = api_client.get(f"/api/v1/dsms/tenants/{tenant_id}/spaces", params={"skip": 0, "limit": 20}, headers=h)
    assert r.status_code == 200, r.text
    space_id = r.json()["items"][0]["id"]
    base = f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}"

    r = api_client.get(f"{base}/business-functions", headers=h)
    assert r.status_code == 200, r.text
    assert len(r.json()) >= 1

    r = api_client.get(f"{base}/submission-tasks", params={"skip": 0, "limit": 50}, headers=h)
    assert r.status_code == 200, r.text
    assert "items" in r.json()

    r = api_client.get(f"{base}/taxonomy-levels", params={"skip": 0, "limit": 20}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 4

    r = api_client.get(f"{base}/questionnaires/questions", params={"skip": 0, "limit": 50}, headers=h)
    assert r.status_code == 200, r.text

    r = api_client.get(f"{base}/relevance/rules", headers=h)
    assert r.status_code == 200, r.text

    r = api_client.get(f"{base}/forms/lifecycle-field-config", params={"skip": 0, "limit": 50}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 2

    r = api_client.get(f"{base}/sensitivity-levels", params={"skip": 0, "limit": 20}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["total"] >= 4

    r = api_client.get(f"{base}/approval-requests", params={"skip": 0, "limit": 20}, headers=h)
    assert r.status_code == 200, r.text

    r = api_client.get(f"{base}/field-catalog", params={"skip": 0, "limit": 50}, headers=h)
    assert r.status_code == 200, r.text

    # 创建草稿任务并下发需已绑 FO；仅验证 POST 创建
    r_fn = api_client.get(f"{base}/business-functions", headers=h)
    fn_key = r_fn.json()[0]["function_key"]
    title = f"pytest-task-{uuid.uuid4().hex[:8]}"
    r = api_client.post(
        f"{base}/submission-tasks",
        json={"function_key": fn_key, "title": title, "internal_note": "pytest"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    assert r.json()["title"] == title

    r = api_client.patch(
        f"{base}/submission-tasks/{task_id}",
        json={"fields": {"foFillStatus": "draft", "foWorkflowStep": "relevance"}},
        headers=h,
    )
    assert r.status_code == 200, r.text


def test_field_catalog_taxonomy_code_update(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 1}, headers=h)
    tenant_id = r.json()["items"][0]["id"]
    r = api_client.get(f"/api/v1/dsms/tenants/{tenant_id}/spaces", params={"skip": 0, "limit": 1}, headers=h)
    space_id = r.json()["items"][0]["id"]
    base = f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}"

    node_code = f"PY.TFC.{uuid.uuid4().hex[:6].upper()}"
    r = api_client.post(
        f"{base}/taxonomy/nodes",
        json={"code": node_code, "name": "pytest 分类节点", "parent_id": None, "sort_order": 0},
        headers=h,
    )
    assert r.status_code == 200, r.text

    r = api_client.get(f"{base}/field-catalog", params={"skip": 0, "limit": 1}, headers=h)
    assert r.status_code == 200, r.text
    entry = r.json()["items"][0]
    entry_id = entry["id"]

    r = api_client.put(
        f"{base}/field-catalog/{entry_id}",
        json={
            "field_name": entry["field_name"],
            "identifier_key": entry["identifier_key"],
            "data_type": entry.get("data_type") or "string",
            "taxonomy_code": node_code,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["taxonomy_code"] == node_code

    r = api_client.put(
        f"{base}/field-catalog/{entry_id}",
        json={
            "field_name": entry["field_name"],
            "identifier_key": entry["identifier_key"],
            "data_type": entry.get("data_type") or "string",
            "taxonomy_code": None,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["taxonomy_code"] is None


def test_classification_rule_recompute_flow(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 1}, headers=h)
    tenant_id = r.json()["items"][0]["id"]
    r = api_client.get(f"/api/v1/dsms/tenants/{tenant_id}/spaces", params={"skip": 0, "limit": 1}, headers=h)
    space_id = r.json()["items"][0]["id"]
    base = f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}"

    r = api_client.get(f"{base}/field-catalog", params={"skip": 0, "limit": 1}, headers=h)
    assert r.status_code == 200, r.text
    entry = r.json()["items"][0]
    entry_id = entry["id"]
    identifier = entry["identifier_key"]

    r = api_client.post(
        f"{base}/classification/rules",
        json={
            "name": f"pytest-rule-{uuid.uuid4().hex[:6]}",
            "priority": 10,
            "condition_json": json.dumps({"type": "identifier_contains", "value": identifier[:4]}),
            "output_sensitivity": "内部",
            "is_active": True,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    rule_id = r.json()["id"]

    r = api_client.post(f"{base}/classification/recompute", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["updated_count"] >= 1

    r = api_client.get(f"{base}/classification/results", params={"skip": 0, "limit": 50}, headers=h)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    matched = [x for x in items if x["field_catalog_entry_id"] == entry_id]
    assert matched, "expected result row for catalog entry"
    assert matched[0]["matched_rule_id"] == rule_id

    api_client.delete(f"{base}/classification/rules/{rule_id}", headers=h)


def test_classification_audit_and_export(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 1}, headers=h)
    tenant_id = r.json()["items"][0]["id"]
    r = api_client.get(f"/api/v1/dsms/tenants/{tenant_id}/spaces", params={"skip": 0, "limit": 1}, headers=h)
    space_id = r.json()["items"][0]["id"]
    base = f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}"

    r = api_client.post(f"{base}/classification/recompute", headers=h)
    assert r.status_code == 200, r.text

    r = api_client.get(f"{base}/classification/audit", params={"skip": 0, "limit": 10}, headers=h)
    assert r.status_code == 200, r.text
    assert "items" in r.json()
    assert any(x["behavior_key"] == "classification-recompute" for x in r.json()["items"])

    r = api_client.get(f"{base}/classification/export", headers=h)
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    assert "result_id" in r.text


def test_platform_user_management(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    r = api_client.get("/api/v1/dsms/platform/users/import-excel/template", headers=h)
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers.get("content-type", "")

    r = api_client.get("/api/v1/dsms/platform/tenant-creators", headers=h)
    assert r.status_code == 200, r.text
    assert "user_ids" in r.json()

    r = api_client.get("/api/v1/dsms/users", params={"skip": 0, "limit": 5}, headers=h)
    assert r.status_code == 200, r.text
    users = r.json()["items"]
    fo_users = [u for u in users if u.get("platform_role") == "function_fo" and not u.get("is_superuser")]
    if fo_users:
        uid = fo_users[0]["id"]
        r = api_client.put(
            "/api/v1/dsms/platform/users/batch-platform-role",
            json={"user_ids": [uid], "platform_role": "function_fo"},
            headers=h,
        )
        assert r.status_code == 200, r.text
        assert uid in r.json()["updated_user_ids"]

    inactive = [u for u in users if u.get("is_active") and not u.get("is_superuser") and u["username"] != settings.first_superuser]
    if inactive:
        uid = inactive[0]["id"]
        r = api_client.post(
            "/api/v1/dsms/platform/users/batch-deactivate",
            json={"user_ids": [uid]},
            headers=h,
        )
        assert r.status_code == 200, r.text
        assert uid in r.json()["deactivated_user_ids"]


def test_copy_approved_submission_tasks(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 5}, headers=h)
    source_tenant_id = r.json()["items"][0]["id"]
    r = api_client.get(
        f"/api/v1/dsms/tenants/{source_tenant_id}/spaces", params={"skip": 0, "limit": 1}, headers=h
    )
    source_space_id = r.json()["items"][0]["id"]
    base = f"/api/v1/dsms/tenants/{source_tenant_id}/spaces/{source_space_id}"

    r = api_client.post(
        f"{base}/submission-tasks",
        json={"function_key": "field_usage", "title": "pytest 已审任务", "internal_note": ""},
        headers=h,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]

    r = api_client.patch(
        f"{base}/submission-tasks/{task_id}",
        json={
            "fields": {
                "status": "dispatched",
                "foFillStatus": "submitted",
                "foFillLifecycleRows": [
                    {"data_field": "用户手机号", "business_function": "field_usage"}
                ],
            }
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    r = api_client.patch(
        f"{base}/submission-tasks/{task_id}",
        json={"fields": {"auditStatus": "approved", "auditComment": "pytest 审核通过"}},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("auditStatus") == "approved"

    slug = f"pytest-copy-{uuid.uuid4().hex[:8]}"
    r = api_client.post("/api/v1/dsms/tenants", json={"name": "复制填报目标", "slug": slug}, headers=h)
    assert r.status_code == 200, r.text
    target_tenant_id = r.json()["id"]
    r = api_client.post(f"/api/v1/dsms/tenants/{target_tenant_id}/seeds/import", headers=h)
    target_space_id = r.json()["space_id"]

    r = api_client.post(
        f"/api/v1/dsms/tenants/{target_tenant_id}/spaces/{target_space_id}/submission-tasks/copy-approved-from",
        json={
            "source_tenant_id": source_tenant_id,
            "source_project_space_id": source_space_id,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("copied_count", 0) >= 1
    assert body.get("behavior_key") == "dsms-submission-tasks-copy-approved"

    r = api_client.get(
        f"/api/v1/dsms/tenants/{target_tenant_id}/spaces/{target_space_id}/submission-tasks",
        params={"skip": 0, "limit": 50},
        headers=h,
    )
    titles = [t["title"] for t in r.json()["items"]]
    assert "pytest 已审任务" in titles


def test_delete_tenant(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    slug = f"pytest-del-{uuid.uuid4().hex[:8]}"
    r = api_client.post("/api/v1/dsms/tenants", json={"name": "待删除项目", "slug": slug}, headers=h)
    assert r.status_code == 200, r.text
    tenant_id = r.json()["id"]

    r = api_client.delete(f"/api/v1/dsms/tenants/{tenant_id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json().get("behavior_key") == "dsms-tenant-delete"

    r = api_client.get(f"/api/v1/dsms/tenants/{tenant_id}", headers=h)
    assert r.status_code == 404


def test_delete_default_tenant_forbidden(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 50}, headers=h)
    default = next((t for t in r.json()["items"] if t.get("slug") == "default"), None)
    if not default:
        return
    r = api_client.delete(f"/api/v1/dsms/tenants/{default['id']}", headers=h)
    assert r.status_code == 400


def test_create_tenant_seeds_import(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    slug = f"pytest-tenant-{uuid.uuid4().hex[:8]}"
    r = api_client.post("/api/v1/dsms/tenants", json={"name": "pytest 项目", "slug": slug}, headers=h)
    assert r.status_code == 200, r.text
    tenant_id = r.json()["id"]

    r = api_client.post(f"/api/v1/dsms/tenants/{tenant_id}/seeds/import", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("space_id")
    assert body.get("behavior_key") == "dsms-seeds-import"


def test_admin_set_user_fo_bindings(api_client):
    from app.core.config import settings

    r = api_client.post(
        "/api/v1/auth/login",
        json={"username": settings.first_superuser, "password": settings.first_superuser_password},
    )
    assert r.status_code == 200, r.text
    h = _auth(r.json()["access_token"])

    r = api_client.get("/api/v1/dsms/tenants", params={"skip": 0, "limit": 1}, headers=h)
    tenant_id = r.json()["items"][0]["id"]
    r = api_client.get(f"/api/v1/dsms/tenants/{tenant_id}/spaces", params={"skip": 0, "limit": 1}, headers=h)
    space_id = r.json()["items"][0]["id"]
    base = f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}"

    r = api_client.get("/api/v1/dsms/users", params={"skip": 0, "limit": 50}, headers=h)
    fo_user = next((u for u in r.json()["items"] if u.get("platform_role") == "function_fo"), None)
    if not fo_user:
        return

    r = api_client.put(
        f"{base}/fo-function-bindings/users/{fo_user['id']}",
        json={"function_keys": ["field_usage"]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert "field_usage" in r.json()["function_keys"]
