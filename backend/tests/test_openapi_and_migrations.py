"""不依赖外置数据库文件的轻量校验（OpenAPI 契约 + SQLite 列迁移）。"""

from sqlalchemy import create_engine, text


def test_openapi_contains_phase23_paths():
    from app.main import app

    paths = app.openapi().get("paths", {})
    keys = list(paths.keys())
    assert any("/classification/matrix" in k for k in keys)
    assert any("/classification/recompute" in k for k in keys)
    assert any("/fields/security-requirements/evaluate" in k for k in keys)
    assert any("/governance/change-logs" in k for k in keys)
    assert any("/config/export" in k for k in keys)
    assert any("/documents/modules" in k for k in keys)
    assert any("/documents/resources" in k for k in keys)
    tenant_detail = paths.get("/api/v1/dsms/tenants/{tenant_id}", {})
    assert "delete" in tenant_detail
    copy_path = "/api/v1/dsms/tenants/{tenant_id}/spaces/{space_id}/submission-tasks/copy-approved-from"
    assert "post" in paths.get(copy_path, {})


def test_sqlite_migration_adds_taxonomy_column():
    from app.core.sqlite_migrations import _ensure_sqlite_phase_columns

    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    with eng.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE fieldcatalogentry (id INTEGER PRIMARY KEY, "
                "tenant_id INTEGER, project_space_id INTEGER, field_name VARCHAR, identifier_key VARCHAR)"
            )
        )
        _ensure_sqlite_phase_columns(conn)
        rows = conn.execute(text("PRAGMA table_info(fieldcatalogentry)")).fetchall()
        names = {r[1] for r in rows}
        assert "taxonomy_code" in names
