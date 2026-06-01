"""DSMS 业务 API 共享工具（分页、空间校验、导入密码等）。"""

import re
import secrets
import string

from fastapi import HTTPException, status
from sqlmodel import Session

from app.models import ProjectSpace


def page_limit(limit: int) -> int:
    if limit > 500:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit 最大值为 500")
    return max(limit, 1)


def get_space_or_404(session: Session, tenant_id: int, space_id: int) -> ProjectSpace:
    space = session.get(ProjectSpace, space_id)
    if not space or space.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目空间不存在")
    return space


def suggest_identifier_key_from_seed(seed: str) -> str:
    s = seed.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    if not s:
        h = abs(hash(seed)) % (10**8)
        s = f"field_{h}"
    return s[:80]


def generate_temporary_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
