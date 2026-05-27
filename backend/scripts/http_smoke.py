"""HTTP 冒烟：对已运行的 uvicorn 实例做登录与关键 GET 探测。"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
PASSWORDS = {
    "admin": "Admin123456",
    "security_fo": "SecurityFo123456",
    "function_fo": "FunctionFo123456",
}


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = raw[:200]
        return exc.code, detail


def main() -> int:
    results: list[tuple[str, bool, str]] = []
    failed = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failed
        results.append((name, ok, detail))
        if not ok:
            failed += 1

    tokens: dict[str, str] = {}
    for user, pwd in PASSWORDS.items():
        code, data = req("POST", "/api/v1/auth/login", body={"username": user, "password": pwd})
        ok = code == 200 and isinstance(data, dict) and bool(data.get("access_token"))
        check(f"login:{user}", ok, str(code) if not ok else "ok")
        if ok:
            tokens[user] = data["access_token"]

    admin = tokens.get("admin")
    if not admin:
        print("SMOKE ABORT: admin login failed")
        return 1

    for user, tok in tokens.items():
        code, data = req("GET", "/api/v1/users/me", token=tok)
        ok = code == 200 and isinstance(data, dict) and data.get("username") == user
        role = data.get("platform_role", "") if isinstance(data, dict) else ""
        check(f"users/me:{user}", ok, role if ok else str(data))

    code, data = req("GET", "/api/v1/dsms/tenants?skip=0&limit=100", token=admin)
    ok = code == 200 and isinstance(data, dict) and "items" in data and data.get("total", 0) >= 1
    check("GET tenants", ok, str(code))
    tenant_id = None
    if ok:
        default_t = next((t for t in data["items"] if t.get("slug") == "default"), None)
        tenant_id = (default_t or data["items"][0])["id"]

    space_id = None
    if tenant_id:
        code, data = req("GET", f"/api/v1/dsms/tenants/{tenant_id}/spaces?skip=0&limit=20", token=admin)
        ok = code == 200 and isinstance(data, dict) and data.get("items")
        check("GET spaces", ok, str(code))
        if ok:
            default_s = next((s for s in data["items"] if s.get("space_key") == "default"), None)
            space_id = (default_s or data["items"][0])["id"]

    prefix = f"/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}" if tenant_id and space_id else None

    if prefix:
        endpoints = [
            ("GET business-functions", "GET", f"{prefix}/business-functions"),
            ("GET submission-tasks", "GET", f"{prefix}/submission-tasks?skip=0&limit=20"),
            ("GET approval-requests", "GET", f"{prefix}/approval-requests?skip=0&limit=20"),
            ("GET pending-count", "GET", f"{prefix}/approval-requests/pending-count"),
            ("GET field-catalog", "GET", f"{prefix}/field-catalog?skip=0&limit=20"),
            ("GET taxonomy-levels", "GET", f"{prefix}/taxonomy-levels?skip=0&limit=20"),
            ("GET questionnaire", "GET", f"{prefix}/questionnaires/questions?skip=0&limit=20"),
            ("GET lifecycle-config", "GET", f"{prefix}/forms/lifecycle-field-config"),
            ("GET members", "GET", f"/api/v1/dsms/tenants/{tenant_id}/members?skip=0&limit=20"),
            ("GET documents/modules", "GET", f"/api/v1/dsms/tenants/{tenant_id}/documents/modules"),
            ("GET classification-results", "GET", f"{prefix}/classification/results?skip=0&limit=20"),
            ("GET security-requirements", "GET", f"{prefix}/fields/security-requirements?skip=0&limit=20"),
            ("GET sensitivity-levels", "GET", f"{prefix}/sensitivity-levels?skip=0&limit=20"),
        ]
        for name, method, path in endpoints:
            code, payload = req(method, path, token=admin)
            ok = code == 200
            extra = str(code)
            if ok and isinstance(payload, dict) and "total" in payload:
                extra = f"total={payload.get('total')}"
            elif ok and isinstance(payload, dict) and isinstance(payload.get("items"), list):
                extra = f"items={len(payload['items'])}"
            elif ok and isinstance(payload, list):
                extra = f"list={len(payload)}"
            check(name, ok, extra)

    sec = tokens.get("security_fo")
    if sec and prefix:
        code, _ = req("GET", f"{prefix}/approval-requests/pending-count", token=sec)
        check("security_fo pending-count", code == 200, str(code))

    fo = tokens.get("function_fo")
    if fo and prefix:
        code, payload = req("GET", f"{prefix}/fo-function-bindings/me", token=fo)
        extra = str(payload)[:80] if payload else str(code)
        check("function_fo fo-function-bindings/me", code == 200, extra)

    code, _ = req("GET", "/openapi.json")
    check("GET openapi.json", code == 200, str(code))

    print("=== HTTP Smoke Results ===")
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        line = f"[{mark}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)
    print(f"--- {len(results) - failed}/{len(results)} passed ---")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
