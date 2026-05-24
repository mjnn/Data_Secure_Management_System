from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def _ensure_sqlite_phase_columns(conn) -> None:
    """SQLite：create_all 不会为已存在表补列，此处做最小演进迁移。"""
    rows = conn.execute(text("PRAGMA table_info(fieldcatalogentry)")).fetchall()
    col_names = {r[1] for r in rows}
    if "taxonomy_code" not in col_names:
        conn.execute(text("ALTER TABLE fieldcatalogentry ADD COLUMN taxonomy_code VARCHAR"))


def _ensure_user_platform_role_column(conn) -> None:
    rows = conn.execute(text("PRAGMA table_info(user)")).fetchall()
    col_names = {r[1] for r in rows}
    if "platform_role" not in col_names:
        conn.execute(text("ALTER TABLE user ADD COLUMN platform_role VARCHAR DEFAULT 'security_fo'"))
    conn.execute(text("UPDATE user SET platform_role = 'system_admin' WHERE is_superuser = 1"))
    conn.execute(text("UPDATE user SET platform_role = 'security_fo' WHERE platform_role IS NULL OR platform_role = ''"))


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    if settings.database_url.startswith("sqlite"):
        with engine.begin() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            _ensure_sqlite_phase_columns(conn)
            _ensure_user_platform_role_column(conn)


def get_session():
    with Session(engine) as session:
        yield session
