from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.core.sqlite_migrations import run_sqlite_migrations

# 注册全部 ORM 表（含 models_portal）
import app.models  # noqa: F401


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    if settings.database_url.startswith("sqlite"):
        with engine.begin() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            run_sqlite_migrations(conn)


def get_session():
    with Session(engine) as session:
        yield session
