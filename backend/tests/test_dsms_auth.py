"""dsms_auth 角色校验。"""

import pytest
from fastapi import HTTPException

from app.api.dsms_auth import has_function_fo_role, is_function_fo, is_staff, require_function_fo, require_staff
from app.models import User


def _user(**kwargs) -> User:
    return User(
        username=kwargs.get("username", "u"),
        email=kwargs.get("email", "u@local.dsms"),
        hashed_password="x",
        platform_role=kwargs.get("platform_role", "security_fo"),
        is_superuser=kwargs.get("is_superuser", False),
    )


def test_is_staff_matches_require_staff_gate():
    assert is_staff(_user(platform_role="security_fo")) is True
    assert is_staff(_user(platform_role="function_fo")) is False


def test_has_function_fo_role_is_strict():
    assert has_function_fo_role(_user(platform_role="function_fo")) is True
    assert has_function_fo_role(_user(is_superuser=True)) is False


def test_require_staff_allows_security_fo_and_superuser():
    assert require_staff(_user(platform_role="security_fo")).platform_role == "security_fo"
    assert require_staff(_user(is_superuser=True)).is_superuser is True


def test_require_staff_rejects_function_fo():
    with pytest.raises(HTTPException) as exc:
        require_staff(_user(platform_role="function_fo"))
    assert exc.value.status_code == 403


def test_require_function_fo_allows_function_fo_and_superuser():
    assert require_function_fo(_user(platform_role="function_fo")).platform_role == "function_fo"
    assert require_function_fo(_user(is_superuser=True)).is_superuser is True


def test_require_function_fo_rejects_security_fo():
    with pytest.raises(HTTPException) as exc:
        require_function_fo(_user(platform_role="security_fo"))
    assert exc.value.status_code == 403
