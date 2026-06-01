"""Phase 3 治理日志、配置导入导出与合并导出。"""

import csv
import io
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from app.api.dsms_helpers import get_space_or_404, page_limit
from app.core.deps import require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import (
    ClassificationMatrix,
    ClassificationResult,
    ClassificationRule,
    FieldCatalogEntry,
    FieldUsageReport,
    FieldUsageReportItem,
    GovernanceChangeLog,
    User,
)
from app.schemas import ConfigBatchDeleteIn, ConfigImportIn, GovernanceChangeLogOut, Page
from app.services.config_service import export_space_config, governance_log, import_space_config

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-phase23-governance"])


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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, target_tid, target_sid)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
