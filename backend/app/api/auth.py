from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from app.core.auth_limits import auth_rate_limit
from app.core.database import get_session
from app.core.security import verify_password
from app.models import User
from app.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.services.token_service import issue_auth_tokens, logout_refresh_token, rotate_refresh_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    description="权限：公开接口。用户名密码登录，返回 access/refresh token。",
)
@auth_rate_limit("10/minute")
def login(request: Request, payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")
    return issue_auth_tokens(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    description="权限：公开接口。使用 refresh_token 换新 token（单次轮换，旧 refresh 立即失效）。",
)
@auth_rate_limit("20/minute")
def refresh(request: Request, payload: RefreshRequest, session: Session = Depends(get_session)) -> TokenResponse:
    try:
        return rotate_refresh_token(session, payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效") from exc


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    description="权限：公开接口。吊销当前 refresh_token（客户端仍须清除本地令牌）。",
)
def logout(payload: RefreshRequest, session: Session = Depends(get_session)) -> Response:
    logout_refresh_token(session, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
