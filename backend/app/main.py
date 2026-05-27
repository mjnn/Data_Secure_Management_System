import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from app.api.auth import router as auth_router
from app.api.dsms import router as dsms_router
from app.api.dsms_portal import router as dsms_portal_router
from app.api.dsms_phase23 import router as dsms_phase23_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.database import create_db_and_tables, engine
from app.core.security import get_password_hash
from app.models import User
from app.services.portal_seed import ensure_portal_seed

_TEST_SECURITY_FO_USERNAME = "security_fo"
_TEST_FUNCTION_FO_USERNAME = "function_fo"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == settings.first_superuser)).first()
        if not existing:
            admin = User(
                username=settings.first_superuser,
                email=f"{settings.first_superuser}@local.dsms",
                hashed_password=get_password_hash(settings.first_superuser_password),
                full_name="系统管理员",
                platform_role="system_admin",
                is_superuser=True,
                is_active=True,
                is_approved=True,
            )
            session.add(admin)
            session.commit()

        # 门户测试账号：数据安全 FO、功能 FO（已存在则跳过）
        if not session.exec(select(User).where(User.username == _TEST_SECURITY_FO_USERNAME)).first():
            session.add(
                User(
                    username=_TEST_SECURITY_FO_USERNAME,
                    email="security_fo@local.dsms",
                    hashed_password=get_password_hash(settings.test_security_fo_password),
                    full_name="数据安全FO（测试）",
                    platform_role="security_fo",
                    is_superuser=False,
                    is_active=True,
                    is_approved=True,
                )
            )
        if not session.exec(select(User).where(User.username == _TEST_FUNCTION_FO_USERNAME)).first():
            session.add(
                User(
                    username=_TEST_FUNCTION_FO_USERNAME,
                    email="function_fo@local.dsms",
                    hashed_password=get_password_hash(settings.test_function_fo_password),
                    full_name="功能FO（测试）",
                    platform_role="function_fo",
                    is_superuser=False,
                    is_active=True,
                    is_approved=True,
                )
            )
        session.commit()
        ensure_portal_seed(session)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(dsms_router)
app.include_router(dsms_portal_router)
app.include_router(dsms_phase23_router)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


_static_dir = os.environ.get("STATIC_DIR", "").strip()
if _static_dir:
    _static_path = Path(_static_dir)
    if _static_path.is_dir():
        _assets = _static_path / "assets"
        if _assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(_assets)), name="static-assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            if full_path.startswith("api/"):
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="未找到")
            candidate = _static_path / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            index = _static_path / "index.html"
            if index.is_file():
                return FileResponse(index)
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="未找到")
