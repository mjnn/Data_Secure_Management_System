from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import decode_token
from app.models import TenantMembership, User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌类型错误")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或不可用")
    return user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可执行该操作")
    return current_user


def get_membership(session: Session, tenant_id: int, user_id: int) -> TenantMembership | None:
    return session.exec(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
        )
    ).first()


def require_tenant_member(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    if current_user.is_superuser:
        return current_user
    membership = get_membership(session, tenant_id, current_user.id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您不属于该项目，无法访问")
    return current_user


def require_tenant_admin(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    if current_user.is_superuser:
        return current_user
    membership = get_membership(session, tenant_id, current_user.id)
    if not membership or membership.role != "tenant_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅项目管理员可执行该操作")
    return current_user
