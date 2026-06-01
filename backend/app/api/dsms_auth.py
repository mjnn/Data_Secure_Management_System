"""DSMS API 层角色校验（portal / 服务层复用）。"""

from fastapi import HTTPException, status

from app.models import User

STAFF_PLATFORM_ROLES = frozenset({"system_admin", "security_fo"})


def is_staff(user: User) -> bool:
    return user.is_superuser or user.platform_role in STAFF_PLATFORM_ROLES


def is_function_fo(user: User) -> bool:
    return user.is_superuser or user.platform_role == "function_fo"


def has_function_fo_role(user: User) -> bool:
    return user.platform_role == "function_fo"


def require_staff(user: User) -> User:
    if not is_staff(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅数据安全 FO 或系统管理员可执行该操作")
    return user


def require_function_fo(user: User) -> User:
    if not is_function_fo(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅功能 FO 可执行该操作")
    return user
