import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from sqlmodel import Session, select

from app.api.auth import router as auth_router
from app.api.dsms_platform import router as dsms_platform_router
from app.api.dsms_space import router as dsms_space_router
from app.api.dsms_portal_approvals import router as dsms_portal_approvals_router
from app.api.dsms_portal_documents import router as dsms_portal_documents_router
from app.api.dsms_portal_tasks import router as dsms_portal_tasks_router
from app.api.dsms_phase23_classification import router as dsms_phase23_classification_router
from app.api.dsms_phase23_fields import router as dsms_phase23_fields_router
from app.api.dsms_phase23_governance import router as dsms_phase23_governance_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.database import create_db_and_tables, engine
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.security import get_password_hash
from app.models import User
from app.services.portal_seed import ensure_portal_seed
from app.services.token_service import purge_expired_revocations

_TEST_SECURITY_FO_USERNAME = "security_fo"
_TEST_FUNCTION_FO_USERNAME = "function_fo"


async def _revocation_purge_loop() -> None:
    interval = settings.refresh_token_purge_interval_seconds
    while True:
        await asyncio.sleep(interval)
        with Session(engine) as session:
            purge_expired_revocations(session)


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

        if settings.should_seed_test_users():
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
        purge_expired_revocations(session)
    purge_task: asyncio.Task | None = None
    if settings.refresh_token_purge_interval_seconds > 0:
        purge_task = asyncio.create_task(_revocation_purge_loop())
    try:
        yield
    finally:
        if purge_task is not None:
            purge_task.cancel()
            try:
                await purge_task
            except asyncio.CancelledError:
                pass


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(dsms_platform_router)
app.include_router(dsms_space_router)
app.include_router(dsms_portal_documents_router)
app.include_router(dsms_portal_tasks_router)
app.include_router(dsms_portal_approvals_router)
app.include_router(dsms_phase23_classification_router)
app.include_router(dsms_phase23_fields_router)
app.include_router(dsms_phase23_governance_router)


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
            if full_path:
                try:
                    from app.core.upload_utils import resolve_path_within_root

                    candidate = resolve_path_within_root(_static_path, full_path)
                except ValueError:
                    from fastapi import HTTPException

                    raise HTTPException(status_code=404, detail="未找到")
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            index = _static_path / "index.html"
            if index.is_file():
                return FileResponse(index)
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="未找到")
