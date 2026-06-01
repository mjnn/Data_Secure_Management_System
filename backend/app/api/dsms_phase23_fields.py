"""Phase 2/3 字段密级绑定与安全要求。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from app.api.dsms_helpers import get_space_or_404, page_limit
from app.core.deps import require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import FieldCatalogEntry, FieldClassGrade, FieldSecurityRequirement, User
from app.schemas import (
    FieldClassGradeOut,
    FieldClassGradePutIn,
    FieldSecurityEvalIn,
    FieldSecurityEvalItemOut,
    FieldSecurityEvalOut,
    FieldSecurityRequirementCreateIn,
    FieldSecurityRequirementOut,
    FieldSecurityRequirementUpdateIn,
    Page,
)
from app.services.classification_service import evaluate_security_for_entries
from app.services.config_service import governance_log

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-phase23-fields"])


# --- field class grade ---


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/fields/class-grade",
    response_model=Page,
    description="权限：tenant_member+。字段密级绑定分页。",
)
def list_field_class_grades(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    get_space_or_404(session, tenant_id, space_id)
    stmt = select(FieldClassGrade).where(
        FieldClassGrade.tenant_id == tenant_id,
        FieldClassGrade.project_space_id == space_id,
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(stmt.order_by(FieldClassGrade.id.desc()).offset(skip).limit(limit)).all()
    return {
        "total": total,
        "items": [FieldClassGradeOut.model_validate(r, from_attributes=True).model_dump() for r in rows],
    }


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/fields/class-grade",
    description="权限：tenant_admin+。批量写入字段密级。",
)
def put_field_class_grades(
    tenant_id: int,
    space_id: int,
    payload: FieldClassGradePutIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    for row in payload.grades:
        fe = session.get(FieldCatalogEntry, row.field_catalog_entry_id)
        if not fe or fe.tenant_id != tenant_id or fe.project_space_id != space_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"主表字段不存在: {row.field_catalog_entry_id}",
            )
        ex = session.exec(
            select(FieldClassGrade).where(
                FieldClassGrade.tenant_id == tenant_id,
                FieldClassGrade.project_space_id == space_id,
                FieldClassGrade.field_catalog_entry_id == row.field_catalog_entry_id,
            )
        ).first()
        if ex:
            ex.grade_label = row.grade_label
            ex.notes = row.notes
            ex.updated_by_user_id = user.id
            ex.updated_at = datetime.now(timezone.utc)
            session.add(ex)
        else:
            session.add(
                FieldClassGrade(
                    tenant_id=tenant_id,
                    project_space_id=space_id,
                    field_catalog_entry_id=row.field_catalog_entry_id,
                    grade_label=row.grade_label,
                    notes=row.notes,
                    updated_by_user_id=user.id,
                )
            )
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-field-class-grade-batch",
        resource_type="field_class_grade",
        resource_id=None,
        summary=f"批量更新密级 {len(payload.grades)} 条",
        detail={},
    )
    session.commit()
    return {"updated": len(payload.grades), "behavior_key": "field-class-grade"}


@router.delete(
    "/tenants/{tenant_id}/spaces/{space_id}/fields/class-grade/{catalog_entry_id}",
    description="权限：tenant_admin+。删除某主表字段密级绑定。",
)
def delete_field_class_grade(
    tenant_id: int,
    space_id: int,
    catalog_entry_id: int,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    ex = session.exec(
        select(FieldClassGrade).where(
            FieldClassGrade.tenant_id == tenant_id,
            FieldClassGrade.project_space_id == space_id,
            FieldClassGrade.field_catalog_entry_id == catalog_entry_id,
        )
    ).first()
    if not ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="密级绑定不存在")
    session.delete(ex)
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-field-class-grade-delete",
        resource_type="field_class_grade",
        resource_id=catalog_entry_id,
        summary="删除密级绑定",
        detail={},
    )
    session.commit()
    return {"deleted_field_catalog_entry_id": catalog_entry_id, "behavior_key": "field-class-grade"}


# --- security requirements ---


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/fields/security-requirements",
    response_model=Page,
    description="权限：tenant_member+。安全要求分页。",
)
def list_security_requirements(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    field_catalog_entry_id: int | None = Query(default=None),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    get_space_or_404(session, tenant_id, space_id)
    stmt = select(FieldSecurityRequirement).where(
        FieldSecurityRequirement.tenant_id == tenant_id,
        FieldSecurityRequirement.project_space_id == space_id,
    )
    if field_catalog_entry_id is not None:
        stmt = stmt.where(FieldSecurityRequirement.field_catalog_entry_id == field_catalog_entry_id)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(stmt.order_by(FieldSecurityRequirement.id.desc()).offset(skip).limit(limit)).all()
    return {
        "total": total,
        "items": [FieldSecurityRequirementOut.model_validate(r, from_attributes=True).model_dump() for r in rows],
    }


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/fields/security-requirements",
    response_model=FieldSecurityRequirementOut,
    description="权限：tenant_admin+。新建安全要求。",
)
def create_security_requirement(
    tenant_id: int,
    space_id: int,
    payload: FieldSecurityRequirementCreateIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    fe = session.get(FieldCatalogEntry, payload.field_catalog_entry_id)
    if not fe or fe.tenant_id != tenant_id or fe.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="主表字段不存在")
    r = FieldSecurityRequirement(
        tenant_id=tenant_id,
        project_space_id=space_id,
        field_catalog_entry_id=payload.field_catalog_entry_id,
        requirement_name=payload.requirement_name,
        check_kind=payload.check_kind,
        check_json=payload.check_json or "{}",
        is_active=payload.is_active,
    )
    session.add(r)
    session.commit()
    session.refresh(r)
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-security-req-create",
        resource_type="field_security_requirement",
        resource_id=r.id,
        summary=f"新建安全要求 {r.requirement_name}",
        detail={},
    )
    session.commit()
    return FieldSecurityRequirementOut.model_validate(r, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/fields/security-requirements/{requirement_id}",
    response_model=FieldSecurityRequirementOut,
    description="权限：tenant_admin+。更新安全要求。",
)
def update_security_requirement(
    tenant_id: int,
    space_id: int,
    requirement_id: int,
    payload: FieldSecurityRequirementUpdateIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    r = session.get(FieldSecurityRequirement, requirement_id)
    if not r or r.tenant_id != tenant_id or r.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="安全要求不存在")
    r.requirement_name = payload.requirement_name
    r.check_kind = payload.check_kind
    r.check_json = payload.check_json or "{}"
    r.is_active = payload.is_active
    session.add(r)
    session.commit()
    session.refresh(r)
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-security-req-update",
        resource_type="field_security_requirement",
        resource_id=r.id,
        summary=f"更新安全要求 {r.requirement_name}",
        detail={},
    )
    session.commit()
    return FieldSecurityRequirementOut.model_validate(r, from_attributes=True)


@router.delete(
    "/tenants/{tenant_id}/spaces/{space_id}/fields/security-requirements/{requirement_id}",
    description="权限：tenant_admin+。删除安全要求。",
)
def delete_security_requirement(
    tenant_id: int,
    space_id: int,
    requirement_id: int,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    r = session.get(FieldSecurityRequirement, requirement_id)
    if not r or r.tenant_id != tenant_id or r.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="安全要求不存在")
    session.delete(r)
    session.commit()
    return {"deleted_id": requirement_id, "behavior_key": "field-security-requirements/delete"}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/fields/security-requirements/evaluate",
    response_model=FieldSecurityEvalOut,
    description="权限：tenant_member+。对安全要求进行逻辑求值。",
)
def evaluate_security_requirements(
    tenant_id: int,
    space_id: int,
    payload: FieldSecurityEvalIn | None = None,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    ids = payload.field_catalog_entry_ids if payload else None
    raw = evaluate_security_for_entries(session, tenant_id, space_id, ids)
    items = [FieldSecurityEvalItemOut.model_validate(x) for x in raw]
    return FieldSecurityEvalOut(items=items, behavior_key="field-security-requirements-eval")


