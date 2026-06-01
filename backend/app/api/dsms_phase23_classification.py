"""Phase 2 分类矩阵、规则、结果与审计。"""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from app.api.dsms_helpers import get_space_or_404, page_limit
from app.api.dsms_phase23_helpers import log_classification_audit
from app.core.deps import require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import (
    ClassificationAuditLog,
    ClassificationMatrix,
    ClassificationResult,
    ClassificationRule,
    FieldCatalogEntry,
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
    Page,
)
from app.services.classification_service import recompute_single_entry, recompute_space
from app.services.config_service import governance_log

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-phase23-classification"])


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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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


