from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.core.deps import get_current_user
from app.core.database import get_session
from app.core.security import get_password_hash, verify_password
from app.models import User, utc_now
from app.schemas import UserMeOut, UserMeUpdateIn, UserPasswordChangeIn

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserMeOut,
    description="权限：super_admin / tenant_admin / tenant_member（任意已登录用户）。",
)
def get_me(current_user: User = Depends(get_current_user)) -> UserMeOut:
    return UserMeOut.model_validate(current_user, from_attributes=True)


@router.put(
    "/me",
    response_model=UserMeOut,
    description="权限：任意已登录用户。仅允许更新白名单字段：email / full_name / department。",
)
def update_me(
    payload: UserMeUpdateIn,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserMeOut:
    if payload.email is not None and payload.email != current_user.email:
        exists = session.exec(
            select(User).where(User.email == payload.email, User.id != current_user.id)
        ).first()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被其他账号使用",
            )
        current_user.email = payload.email
    if payload.full_name is not None:
        current_user.full_name = payload.full_name or None
    if payload.department is not None:
        current_user.department = payload.department or None
    current_user.updated_at = utc_now()
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return UserMeOut.model_validate(current_user, from_attributes=True)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    description="权限：任意已登录用户。自助修改密码，需校验原密码。",
)
def change_my_password(
    payload: UserPasswordChangeIn,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )
    if payload.new_password == payload.old_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不得与原密码相同",
        )
    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.updated_at = utc_now()
    session.add(current_user)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
