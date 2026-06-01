"""dsms_helpers 分页与空间校验单元测试。"""

import uuid

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.dsms_helpers import get_space_or_404, page_limit
from app.models import ProjectSpace, Tenant


def test_page_limit_clamps_minimum_and_rejects_over_max():
    assert page_limit(0) == 1
    assert page_limit(20) == 20
    with pytest.raises(HTTPException) as exc:
        page_limit(501)
    assert exc.value.status_code == 422


def test_get_space_or_404_rejects_cross_tenant_space():
    from app.core.database import engine

    suffix = uuid.uuid4().hex[:8]
    with Session(engine) as session:
        tenant_a = Tenant(name=f"pytest-a-{suffix}", slug=f"pytest-a-{suffix}")
        tenant_b = Tenant(name=f"pytest-b-{suffix}", slug=f"pytest-b-{suffix}")
        session.add(tenant_a)
        session.add(tenant_b)
        session.commit()
        session.refresh(tenant_a)
        session.refresh(tenant_b)

        space = ProjectSpace(tenant_id=tenant_a.id, space_key="main", name="主空间")
        session.add(space)
        session.commit()
        session.refresh(space)

        found = get_space_or_404(session, tenant_a.id, space.id)
        assert found.id == space.id

        with pytest.raises(HTTPException) as exc:
            get_space_or_404(session, tenant_b.id, space.id)
        assert exc.value.status_code == 404

        session.delete(space)
        session.delete(tenant_a)
        session.delete(tenant_b)
        session.commit()
