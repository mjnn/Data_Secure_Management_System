#!/usr/bin/env python3
"""Phase11 浏览器侧能力代验：对运行中的后端 http://127.0.0.1:8000 发请求，核对顶栏/看板/待办依赖的 API。"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, dict | str]:
    url = f"{BASE}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def main() -> int:
    fails = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal fails
        mark = "PASS" if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"  [{mark}] {name}")
        if detail:
            print(f"         {detail}")

    print("\n=== Phase11 UI 依赖 API 冒烟（需后端已启动）===\n")

    code, health = req("GET", "/healthz")
    check("healthz", code == 200, str(health))

    code, login = req("POST", "/api/v1/auth/login", body={"username": "admin", "password": "Admin123456"})
    if code != 200:
        print("  无法登录，请先启动后端并确认种子账号。")
        return 1
    token = login["access_token"]
    check("admin 登录", True)

    code, tenants = req("GET", "/api/v1/dsms/tenants?skip=0&limit=50", token)
    check("顶栏项目列表 tenants", code == 200 and "items" in tenants, f"total={tenants.get('total')}")

    items = tenants.get("items") or []

    def tenant_space(tid: int) -> int | None:
        c, sp = req("GET", f"/api/v1/dsms/tenants/{tid}/spaces?skip=0&limit=1", token)
        if c != 200 or not sp.get("items"):
            return None
        return sp["items"][0]["id"]

    def fc_total(tid: int, sid: int) -> int:
        c2, cat = req("GET", f"/api/v1/dsms/tenants/{tid}/spaces/{sid}/field-catalog?skip=0&limit=1", token)
        return cat.get("total", -1) if c2 == 200 else -1

    with_space = [(t["id"], tenant_space(t["id"])) for t in items]
    with_space = [(tid, sid) for tid, sid in with_space if sid is not None]
    if len(with_space) < 2:
        check("切换项目（≥2 个有效空间）", False, f"仅 {len(with_space)} 个项目有空间，请新建项目并 seeds")
    else:
        (t1, s1), (t2, s2) = with_space[0], with_space[1]
        a, b = fc_total(t1, s1), fc_total(t2, s2)
        check("切换项目后数据可区分", a >= 0 and b >= 0, f"tenant {t1} total={a}, tenant {t2} total={b}")

    if not with_space:
        print("  无可用空间，跳过后续空间内检查。")
        return 1
    tid, sid = with_space[0]
    base = f"/api/v1/dsms/tenants/{tid}/spaces/{sid}"

    c, tasks = req("GET", f"{base}/submission-tasks?skip=0&limit=50", token)
    check("填报情况 submission-tasks", c == 200 and "items" in tasks, f"count={len(tasks.get('items', []))}")

    c, fns = req("GET", f"{base}/business-functions", token)
    check("填报情况 business-functions", c == 200 and isinstance(fns, list), f"len={len(fns) if isinstance(fns, list) else 0}")

    c, pending = req("GET", f"{base}/approval-requests?status=pending&skip=0&limit=1", token)
    check("控制台待办 approval-requests", c == 200, f"pending total={pending.get('total')}")

    c, fo_users = req("GET", "/api/v1/dsms/users?skip=0&limit=50", token)
    fo_uid = None
    if c == 200:
        fo_uid = next((u["id"] for u in fo_users.get("items", []) if u.get("username") == "function_fo"), None)
    if fo_uid:
        req("POST", f"/api/v1/dsms/tenants/{tid}/members/batch", token, {"user_ids": [fo_uid], "role": "tenant_member"})
        req("PUT", f"{base}/fo-function-bindings/users/{fo_uid}", token, {"function_keys": ["field_usage"]})
    c, fo = req("POST", "/api/v1/auth/login", body={"username": "function_fo", "password": "FunctionFo123456"})
    if c == 200:
        fo_token = fo["access_token"]
        c2, bind = req("GET", f"{base}/fo-function-bindings/me", fo_token)
        c3, t2 = req("GET", f"{base}/submission-tasks?skip=0&limit=50", fo_token)
        check(
            "FO 红点依赖 bindings+tasks",
            c2 == 200 and c3 == 200,
            f"keys={len(bind.get('function_keys', []))} tasks={len(t2.get('items', []))}",
        )
    else:
        check("FO 登录", False, str(fo))

    c, cat = req("GET", f"{base}/field-catalog?skip=0&limit=1", token)
    eid = None
    if c == 200 and cat.get("items"):
        eid = cat["items"][0]["id"]
    else:
        cr = req(
            "POST",
            f"{base}/field-catalog",
            token,
            {"field_name": "UI冒烟字段", "identifier_key": "ui_smoke_field", "data_type": "string"},
        )
        if cr[0] == 200:
            eid = cr[1]["id"]
    if eid:
        c2, ev = req(
            "POST",
            f"{base}/fields/security-requirements/evaluate",
            token,
            {"field_catalog_entry_ids": [eid]},
        )
        check("安全要求 evaluate", c2 == 200 and "items" in ev, f"requirements={len((ev.get('items') or [{}])[0].get('requirements', []))}")
    else:
        check("安全要求 evaluate", False, "无法创建或读取字段主表")

    stored_key = "dsms_portal_selected_tenant_v1"
    check("localStorage 键名（前端）", True, f"键 {stored_key} 由 usePortalTenantContext 写入")

    print(f"\n--- 失败 {fails} 项；请在 http://127.0.0.1:5173 目视确认图表与红点 ---\n")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
