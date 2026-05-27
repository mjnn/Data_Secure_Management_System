"""SQLite 列演进：create_all 不会为已存在表补列。"""

from sqlalchemy import text


def _table_columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def _add_column_if_missing(conn, table: str, column: str, ddl: str) -> None:
    if column not in _table_columns(conn, table):
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def _ensure_sqlite_phase_columns(conn) -> None:
    _add_column_if_missing(conn, "fieldcatalogentry", "taxonomy_code", "taxonomy_code VARCHAR")
    _add_column_if_missing(conn, "fieldcatalogentry", "description", "description VARCHAR")


def _ensure_user_platform_role_column(conn) -> None:
    _add_column_if_missing(conn, "user", "platform_role", "platform_role VARCHAR DEFAULT 'security_fo'")
    conn.execute(text("UPDATE user SET platform_role = 'system_admin' WHERE is_superuser = 1"))
    conn.execute(text("UPDATE user SET platform_role = 'security_fo' WHERE platform_role IS NULL OR platform_role = ''"))


def _ensure_portal_model_columns(conn) -> None:
    _add_column_if_missing(conn, "tenant", "copy_meta_json", "copy_meta_json VARCHAR")
    _add_column_if_missing(conn, "questionnairequestion", "options_json", "options_json VARCHAR")
    _add_column_if_missing(conn, "relevancerule", "logic_root_json", "logic_root_json VARCHAR")
    _add_column_if_missing(conn, "relevancerule", "conclusion_when_true", "conclusion_when_true VARCHAR DEFAULT 'relevant'")
    _add_column_if_missing(conn, "relevancerule", "conclusion_when_false", "conclusion_when_false VARCHAR DEFAULT 'irrelevant'")
    _add_column_if_missing(conn, "lifecyclefieldconfig", "is_builtin", "is_builtin BOOLEAN DEFAULT 0")


def run_sqlite_migrations(conn) -> None:
    _ensure_sqlite_phase_columns(conn)
    _ensure_user_platform_role_column(conn)
    _ensure_portal_model_columns(conn)
