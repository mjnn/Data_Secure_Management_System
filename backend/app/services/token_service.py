"""Refresh token 轮换、吊销与版本校验。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models import RevokedRefreshToken, User
from app.schemas import TokenResponse


def _token_expiry(data: dict) -> datetime:
    exp = data.get("exp")
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    return datetime.now(timezone.utc)


def is_jti_revoked(session: Session, jti: str) -> bool:
    return session.get(RevokedRefreshToken, jti) is not None


def revoke_jti(session: Session, jti: str, username: str, expires_at: datetime) -> None:
    if session.get(RevokedRefreshToken, jti):
        return
    session.add(
        RevokedRefreshToken(
            jti=jti,
            username=username,
            expires_at=expires_at,
        )
    )


def purge_expired_revocations(session: Session) -> None:
    now = datetime.now(timezone.utc)
    rows = session.exec(select(RevokedRefreshToken).where(RevokedRefreshToken.expires_at < now)).all()
    for row in rows:
        session.delete(row)
    if rows:
        session.commit()


def issue_auth_tokens(user: User) -> TokenResponse:
    version = user.refresh_token_version or 0
    access_token = create_access_token(user.username)
    refresh_token, _, _ = create_refresh_token(user.username, version)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def validate_refresh_payload(session: Session, data: dict) -> User:
    if data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌类型错误")
    username = data.get("sub")
    jti = data.get("jti")
    if not username or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效")
    if is_jti_revoked(session, jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌已失效")
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")
    if data.get("ver", 0) != (user.refresh_token_version or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌已失效")
    return user


def rotate_refresh_token(session: Session, refresh_token: str) -> TokenResponse:
    data = decode_token(refresh_token)
    user = validate_refresh_payload(session, data)
    revoke_jti(session, data["jti"], user.username, _token_expiry(data))
    session.commit()
    return issue_auth_tokens(user)


def logout_refresh_token(session: Session, refresh_token: str) -> None:
    try:
        data = decode_token(refresh_token)
    except ValueError:
        return
    if data.get("type") != "refresh":
        return
    jti = data.get("jti")
    username = data.get("sub")
    if not jti or not username:
        return
    revoke_jti(session, jti, username, _token_expiry(data))
    session.commit()


def bump_refresh_token_version(session: Session, user: User) -> None:
    user.refresh_token_version = (user.refresh_token_version or 0) + 1
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
