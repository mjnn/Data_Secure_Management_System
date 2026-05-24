"""Phase 2 / Phase 3 空间内路由（见 docs/DSMS_IMPLEMENTATION_SPEC.md §7.2、§7.3）。"""

import csv
import io
import json
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from app.core.deps import require_super_admin, require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import (
    ClassificationAuditLog,
    ClassificationMatrix,
    ClassificationResult,
    ClassificationRule,
    FieldCatalogEntry,
    FieldClassGrade,
    FieldSecurityRequirement,
    FieldUsageReport,
    FieldUsageReportItem,
    GovernanceChangeLog,
    ProjectSpace,
    User,
)
from app.schemas import (
    ClassificationAuditOut,
    ClassificationManualIn,
    ClassificationMatrixBatchImportIn,
    ClassificationMatrixCreateIn,
    ClassificationMatrixOut,
    ClassificationMatrixUpdateIn,
    ClassificationResultOut,
    ClassificationRuleCreateIn,
    ClassificationRuleOut,
    ClassificationRuleUpdateIn,
    ConfigBatchDeleteIn,
    ConfigImportIn,
    FieldClassGradeOut,
    FieldClassGradePutIn,
    FieldSecurityEvalIn,
    FieldSecurityEvalItemOut,
    FieldSecurityEvalOut,
    FieldSecurityRequirementCreateIn,
    FieldSecurityRequirementOut,
    FieldSecurityRequirementUpdateIn,
    GovernanceChangeLogOut,
    Page,
)
from app.services.classification_service import (
    evaluate_security_for_entries,
    recompute_single_entry,
    recompute_space,
)
from app.services.config_service import export_space_config, governance_log, import_space_config

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-phase23"])


def page_limit(limit: int) -> int:
    if limit > 500:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit 最大值为 500")
    return limit


def space_or_404(session: Session, tenant_id: int, space_id: int) -> ProjectSpace:
    space = session.get(ProjectSpace, space_id)
    if not space or space.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目空间不存在")
    return space


def log_classification_audit(
    session: Session,
    tenant_id: int,
    space_id: int,
    user_id: int,
    behavior_key: str,
    detail: dict | None = None,
) -> None:
    session.add(
        ClassificationAuditLog(
            tenant_id=tenant_id,
            project_space_id=space_id,
            user_id=user_id,
            behavior_key=behavior_key,
            detail_json=json.dumps(detail or {}, ensure_ascii=False),
        )
    )


# --- classification matrix ---


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/matrix",
    response_model=Page,
    description="权限：tenant_member+。分类矩阵分页列表。",
)
def list_classification_matrices(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    space_or_404(session, tenant_id, space_id)
    stmt = select(ClassificationMatrix).where(
        ClassificationMatrix.tenant_id == tenant_id,
        ClassificationMatrix.project_space_id == space_id,
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(stmt.order_by(ClassificationMatrix.id.desc()).offset(skip).limit(limit)).all()
    return {
        "total": total,
        "items": [ClassificationMatrixOut.model_validate(r, from_attributes=True).model_dump() for r in rows],
    }


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/matrix",
    response_model=ClassificationMatrixOut,
    description="权限：tenant_admin+。新建分类矩阵。",
)
def create_classification_matrix(
    tenant_id: int,
    space_id: int,
    payload: ClassificationMatrixCreateIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    m = ClassificationMatrix(
        tenant_id=tenant_id,
        project_space_id=space_id,
        name=payload.name,
        description=payload.description,
        cells_json=payload.cells_json or "[]",
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    log_classification_audit(session, tenant_id, space_id, user.id, "classification-matrix", {"matrix_id": m.id})
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-matrix-create",
        resource_type="classification_matrix",
        resource_id=m.id,
        summary=f"新建分类矩阵 {m.name}",
        detail={"matrix_id": m.id},
    )
    session.commit()
    return ClassificationMatrixOut.model_validate(m, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/matrix",
    response_model=ClassificationMatrixOut,
    description="权限：tenant_admin+。更新分类矩阵（body 含 id）。",
)
def update_classification_matrix(
    tenant_id: int,
    space_id: int,
    payload: ClassificationMatrixUpdateIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    m = session.get(ClassificationMatrix, payload.id)
    if not m or m.tenant_id != tenant_id or m.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类矩阵不存在")
    m.name = payload.name
    m.description = payload.description
    m.cells_json = payload.cells_json or "[]"
    session.add(m)
    session.commit()
    session.refresh(m)
    log_classification_audit(session, tenant_id, space_id, user.id, "classification-matrix", {"matrix_id": m.id})
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-matrix-update",
        resource_type="classification_matrix",
        resource_id=m.id,
        summary=f"更新分类矩阵 {m.name}",
        detail={},
    )
    session.commit()
    return ClassificationMatrixOut.model_validate(m, from_attributes=True)


@router.delete(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/matrix/{matrix_id}",
    description="权限：tenant_admin+。删除分类矩阵。",
)
def delete_classification_matrix(
    tenant_id: int,
    space_id: int,
    matrix_id: int,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    m = session.get(ClassificationMatrix, matrix_id)
    if not m or m.tenant_id != tenant_id or m.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类矩阵不存在")
    session.delete(m)
    log_classification_audit(
        session, tenant_id, space_id, user.id, "classification-matrix/delete", {"matrix_id": matrix_id}
    )
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-matrix-delete",
        resource_type="classification_matrix",
        resource_id=matrix_id,
        summary="删除分类矩阵",
        detail={},
    )
    session.commit()
    return {"deleted_id": matrix_id, "behavior_key": "classification-matrix/delete"}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/matrix/batch-import",
    description="权限：tenant_admin+。批量导入矩阵。",
)
def batch_import_matrices(
    tenant_id: int,
    space_id: int,
    payload: ClassificationMatrixBatchImportIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    created = 0
    for item in payload.items:
        m = ClassificationMatrix(
            tenant_id=tenant_id,
            project_space_id=space_id,
            name=item.name,
            description=item.description,
            cells_json=item.cells_json or "[]",
        )
        session.add(m)
        created += 1
    log_classification_audit(session, tenant_id, space_id, user.id, "classification-matrix", {"batch": created})
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-matrix-batch-import",
        resource_type="classification_matrix",
        resource_id=None,
        summary=f"批量导入分类矩阵 {created} 条",
        detail={"count": created},
    )
    session.commit()
    return {"created_count": created, "behavior_key": "classification-matrix"}


# --- classification rules ---


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/rules",
    response_model=Page,
    description="权限：tenant_member+。分类规则分页。",
)
def list_classification_rules(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    space_or_404(session, tenant_id, space_id)
    stmt = select(ClassificationRule).where(
        ClassificationRule.tenant_id == tenant_id,
        ClassificationRule.project_space_id == space_id,
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(stmt.order_by(ClassificationRule.priority.asc(), ClassificationRule.id.asc()).offset(skip).limit(limit)).all()
    return {
        "total": total,
        "items": [ClassificationRuleOut.model_validate(r, from_attributes=True).model_dump() for r in rows],
    }


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/rules",
    response_model=ClassificationRuleOut,
    description="权限：tenant_admin+。新建分类规则。",
)
def create_classification_rule(
    tenant_id: int,
    space_id: int,
    payload: ClassificationRuleCreateIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    r = ClassificationRule(
        tenant_id=tenant_id,
        project_space_id=space_id,
        name=payload.name,
        priority=payload.priority,
        condition_json=payload.condition_json or "{}",
        output_sensitivity=payload.output_sensitivity,
        is_active=payload.is_active,
    )
    session.add(r)
    session.commit()
    session.refresh(r)
    log_classification_audit(session, tenant_id, space_id, user.id, "classification-rules", {"rule_id": r.id})
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-rule-create",
        resource_type="classification_rule",
        resource_id=r.id,
        summary=f"新建分类规则 {r.name}",
        detail={},
    )
    session.commit()
    return ClassificationRuleOut.model_validate(r, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/rules",
    response_model=ClassificationRuleOut,
    description="权限：tenant_admin+。更新分类规则（body 含 id）。",
)
def update_classification_rule(
    tenant_id: int,
    space_id: int,
    payload: ClassificationRuleUpdateIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    r = session.get(ClassificationRule, payload.id)
    if not r or r.tenant_id != tenant_id or r.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类规则不存在")
    r.name = payload.name
    r.priority = payload.priority
    r.condition_json = payload.condition_json or "{}"
    r.output_sensitivity = payload.output_sensitivity
    r.is_active = payload.is_active
    session.add(r)
    session.commit()
    session.refresh(r)
    log_classification_audit(session, tenant_id, space_id, user.id, "classification-rules", {"rule_id": r.id})
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-rule-update",
        resource_type="classification_rule",
        resource_id=r.id,
        summary=f"更新分类规则 {r.name}",
        detail={},
    )
    session.commit()
    return ClassificationRuleOut.model_validate(r, from_attributes=True)


@router.delete(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/rules/{rule_id}",
    description="权限：tenant_admin+。删除分类规则。",
)
def delete_classification_rule(
    tenant_id: int,
    space_id: int,
    rule_id: int,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    r = session.get(ClassificationRule, rule_id)
    if not r or r.tenant_id != tenant_id or r.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类规则不存在")
    session.delete(r)
    log_classification_audit(
        session, tenant_id, space_id, user.id, "classification-rules/delete", {"rule_id": rule_id}
    )
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-rule-delete",
        resource_type="classification_rule",
        resource_id=rule_id,
        summary="删除分类规则",
        detail={},
    )
    session.commit()
    return {"deleted_id": rule_id, "behavior_key": "classification-rules/delete"}


# --- recompute / results / manual / revert / audit / export ---


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/recompute",
    description="权限：tenant_admin+。对空间内主表字段重算分类结果（跳过人工作覆盖行）。",
)
def classification_recompute(
    tenant_id: int,
    space_id: int,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    n, ids = recompute_space(session, tenant_id, space_id)
    log_classification_audit(
        session,
        tenant_id,
        space_id,
        user.id,
        "classification-recompute",
        {"updated_count": n, "entry_ids_sample": ids[:50]},
    )
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-classification-recompute",
        resource_type="classification",
        resource_id=None,
        summary=f"分类重算 {n} 条",
        detail={"updated_count": n},
    )
    session.commit()
    return {"updated_count": n, "behavior_key": "classification-recompute"}


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/results",
    response_model=Page,
    description="权限：tenant_member+。分类结果分页。",
)
def list_classification_results(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    space_or_404(session, tenant_id, space_id)
    stmt = select(ClassificationResult).where(
        ClassificationResult.tenant_id == tenant_id,
        ClassificationResult.project_space_id == space_id,
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(stmt.order_by(ClassificationResult.id.desc()).offset(skip).limit(limit)).all()
    items = []
    for r in rows:
        fe = session.get(FieldCatalogEntry, r.field_catalog_entry_id)
        d = ClassificationResultOut.model_validate(r, from_attributes=True).model_dump()
        d["field_name"] = fe.field_name if fe else ""
        items.append(d)
    return {"total": total, "items": items}


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/results/{result_id}/manual",
    response_model=ClassificationResultOut,
    description="权限：tenant_admin+。人工覆写分类结果。",
)
def classification_manual_override(
    tenant_id: int,
    space_id: int,
    result_id: int,
    payload: ClassificationManualIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    res = session.get(ClassificationResult, result_id)
    if not res or res.tenant_id != tenant_id or res.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类结果不存在")
    res.is_manual_override = True
    res.manual_level = payload.sensitivity_level
    res.manual_reason = payload.reason
    res.manual_by_user_id = user.id
    res.manual_at = datetime.now(timezone.utc)
    res.sensitivity_level = payload.sensitivity_level
    res.updated_at = datetime.now(timezone.utc)
    session.add(res)
    session.flush()
    log_classification_audit(
        session,
        tenant_id,
        space_id,
        user.id,
        "classification-manual-override",
        {"result_id": result_id, "level": payload.sensitivity_level},
    )
    session.commit()
    session.refresh(res)
    return ClassificationResultOut.model_validate(res, from_attributes=True)


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/results/{result_id}/revert-auto",
    response_model=ClassificationResultOut,
    description="权限：tenant_admin+。恢复自动分类（清除人工标记并重算该字段）。",
)
def classification_revert_auto(
    tenant_id: int,
    space_id: int,
    result_id: int,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    res = session.get(ClassificationResult, result_id)
    if not res or res.tenant_id != tenant_id or res.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类结果不存在")
    entry_id = res.field_catalog_entry_id
    log_classification_audit(
        session, tenant_id, space_id, user.id, "classification-revert-auto", {"result_id": result_id}
    )
    recompute_single_entry(session, tenant_id, space_id, entry_id)
    session.commit()
    res = session.get(ClassificationResult, result_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类结果不存在")
    return ClassificationResultOut.model_validate(res, from_attributes=True)


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/audit",
    response_model=Page,
    description="权限：tenant_member+。分类审计分页。",
)
def list_classification_audit(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    behavior_key: str | None = Query(default=None),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    space_or_404(session, tenant_id, space_id)
    stmt = select(ClassificationAuditLog).where(
        ClassificationAuditLog.tenant_id == tenant_id,
        ClassificationAuditLog.project_space_id == space_id,
    )
    if behavior_key:
        stmt = stmt.where(ClassificationAuditLog.behavior_key == behavior_key)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(stmt.order_by(ClassificationAuditLog.id.desc()).offset(skip).limit(limit)).all()
    return {
        "total": total,
        "items": [ClassificationAuditOut.model_validate(r, from_attributes=True).model_dump() for r in rows],
    }


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/classification/export",
    description="权限：tenant_member+。导出分类结果为 CSV。",
)
def export_classification_results(
    tenant_id: int,
    space_id: int,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    rows = session.exec(
        select(ClassificationResult).where(
            ClassificationResult.tenant_id == tenant_id,
            ClassificationResult.project_space_id == space_id,
        )
    ).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "result_id",
            "field_catalog_entry_id",
            "field_name",
            "sensitivity_level",
            "is_manual_override",
            "matched_rule_id",
            "applied_matrix",
            "updated_at",
        ]
    )
    for r in rows:
        fe = session.get(FieldCatalogEntry, r.field_catalog_entry_id)
        w.writerow(
            [
                r.id,
                r.field_catalog_entry_id,
                fe.field_name if fe else "",
                r.sensitivity_level,
                r.is_manual_override,
                r.matched_rule_id or "",
                r.applied_matrix,
                r.updated_at.isoformat(),
            ]
        )
    data = "\ufeff" + buf.getvalue()
    return StreamingResponse(
        iter([data.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="classification-results.csv"'},
    )


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
    space_or_404(session, tenant_id, space_id)
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
    space_or_404(session, tenant_id, space_id)
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
    space_or_404(session, tenant_id, space_id)
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
    space_or_404(session, tenant_id, space_id)
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
    space_or_404(session, tenant_id, space_id)
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
    space_or_404(session, tenant_id, space_id)
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
    space_or_404(session, tenant_id, space_id)
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
    space_or_404(session, tenant_id, space_id)
    ids = payload.field_catalog_entry_ids if payload else None
    raw = evaluate_security_for_entries(session, tenant_id, space_id, ids)
    items = [FieldSecurityEvalItemOut.model_validate(x) for x in raw]
    return FieldSecurityEvalOut(items=items, behavior_key="field-security-requirements-eval")


# --- Phase 3 governance & config ---


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/governance/change-logs",
    response_model=Page,
    description="权限：tenant_member+。治理变更日志分页；可按 behavior_key / resource_type 筛选。",
)
def list_governance_logs(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    behavior_key: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    space_or_404(session, tenant_id, space_id)
    stmt = select(GovernanceChangeLog).where(
        GovernanceChangeLog.tenant_id == tenant_id,
        GovernanceChangeLog.project_space_id == space_id,
    )
    if behavior_key:
        stmt = stmt.where(GovernanceChangeLog.behavior_key == behavior_key)
    if resource_type:
        stmt = stmt.where(GovernanceChangeLog.resource_type == resource_type)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(stmt.order_by(GovernanceChangeLog.id.desc()).offset(skip).limit(limit)).all()
    return {
        "total": total,
        "items": [GovernanceChangeLogOut.model_validate(r, from_attributes=True).model_dump() for r in rows],
    }


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/config/export",
    description="权限：tenant_admin+。导出空间配置 JSON。",
)
def post_config_export(
    tenant_id: int,
    space_id: int,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    bundle = export_space_config(session, tenant_id, space_id)
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-export",
        resource_type="config",
        resource_id=None,
        summary="导出空间配置",
        detail={"keys": list(bundle.keys())},
    )
    session.commit()
    return {"bundle": bundle, "behavior_key": "dsms-config-export"}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/config/import",
    description="权限：tenant_admin+；super_admin 可指定 target_tenant_id/target_project_space_id。导入配置包。",
)
def post_config_import(
    tenant_id: int,
    space_id: int,
    payload: ConfigImportIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    if not user.is_superuser and (
        payload.target_tenant_id is not None or payload.target_project_space_id is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可指定目标项目或目标空间",
        )
    target_tid = tenant_id
    target_sid = space_id
    if payload.target_tenant_id is not None or payload.target_project_space_id is not None:
        if not user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可指定目标项目/空间")
        if payload.target_tenant_id is None or payload.target_project_space_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="目标项目与目标空间须同时提供")
        target_tid = payload.target_tenant_id
        target_sid = payload.target_project_space_id
    space_or_404(session, target_tid, target_sid)
    try:
        counts = import_space_config(session, target_tid, target_sid, payload.bundle)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    governance_log(
        session,
        tenant_id=target_tid,
        space_id=target_sid,
        user_id=user.id,
        behavior_key="dsms-config-import",
        resource_type="config",
        resource_id=None,
        summary="导入空间配置",
        detail=counts,
    )
    session.commit()
    return {"imported": counts, "behavior_key": "dsms-config-import"}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/config/batch-delete",
    description="权限：tenant_admin+。批量删除矩阵与规则。",
)
def post_config_batch_delete(
    tenant_id: int,
    space_id: int,
    payload: ConfigBatchDeleteIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    deleted_m = 0
    deleted_r = 0
    for mid in payload.classification_matrix_ids or []:
        m = session.get(ClassificationMatrix, mid)
        if m and m.tenant_id == tenant_id and m.project_space_id == space_id:
            session.delete(m)
            deleted_m += 1
    for rid in payload.classification_rule_ids or []:
        r = session.get(ClassificationRule, rid)
        if r and r.tenant_id == tenant_id and r.project_space_id == space_id:
            session.delete(r)
            deleted_r += 1
    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-config-batch-delete",
        resource_type="config",
        resource_id=None,
        summary=f"批量删除 matrix={deleted_m}, rule={deleted_r}",
        detail={"matrices": deleted_m, "rules": deleted_r},
    )
    session.commit()
    return {
        "deleted_matrices": deleted_m,
        "deleted_rules": deleted_r,
        "behavior_key": "dsms-config-batch-delete",
    }


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/exports/consolidated",
    description="权限：tenant_member+。已批准填报与分类结果合并 ZIP 导出。",
)
def get_exports_consolidated(
    tenant_id: int,
    space_id: int,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    space_or_404(session, tenant_id, space_id)
    reports = session.exec(
        select(FieldUsageReport).where(
            FieldUsageReport.tenant_id == tenant_id,
            FieldUsageReport.project_space_id == space_id,
            FieldUsageReport.status == "approved",
        )
    ).all()
    usage_buf = io.StringIO()
    uw = csv.writer(usage_buf)
    uw.writerow(["report_id", "title", "field_name", "value_text"])
    for rep in reports:
        items = session.exec(
            select(FieldUsageReportItem).where(FieldUsageReportItem.report_id == rep.id)
        ).all()
        for it in items:
            uw.writerow([rep.id, rep.title or "", it.field_name, it.value_text])
    cls_buf = io.StringIO()
    cw = csv.writer(cls_buf)
    cw.writerow(["field_catalog_entry_id", "field_name", "sensitivity_level", "is_manual_override"])
    for r in session.exec(
        select(ClassificationResult).where(
            ClassificationResult.tenant_id == tenant_id,
            ClassificationResult.project_space_id == space_id,
        )
    ).all():
        fe = session.get(FieldCatalogEntry, r.field_catalog_entry_id)
        cw.writerow([r.field_catalog_entry_id, fe.field_name if fe else "", r.sensitivity_level, r.is_manual_override])
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("approved_field_usage.csv", "\ufeff" + usage_buf.getvalue())
        zf.writestr("classification_results.csv", "\ufeff" + cls_buf.getvalue())
    zbuf.seek(0)
    return StreamingResponse(
        zbuf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="dsms-consolidated-export.zip"'},
    )
