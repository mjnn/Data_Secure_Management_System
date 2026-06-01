"""填报任务服务（对齐 frontend submissionTasksMock.js）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.api.dsms_auth import has_function_fo_role, is_staff
from app.models import User
from app.models_portal import BusinessFunction, FoUserFunctionBinding, SubmissionTask

STAFF_PATCH_KEYS = frozenset({"auditStatus", "auditComment", "auditedAt", "status"})
FO_PATCH_KEYS = frozenset(
    {
        "foFillStatus",
        "foFillContentSummary",
        "foFillFormSnapshot",
        "foFillLifecycleRows",
        "foCancellationRequested",
        "foCancellationReason",
        "foCancelApprovalPending",
        "foWorkflowStep",
        "foRelevanceConclusion",
        "foRelevanceFillRow",
        "foGovernanceResult",
    }
)
META_PATCH_KEYS = frozenset({"title", "internalNote", "dispatchNote"})
ALLOWED_PATCH_KEYS = STAFF_PATCH_KEYS | FO_PATCH_KEYS | META_PATCH_KEYS


class TaskPatchPermissionError(PermissionError):
    pass


class TaskPatchValidationError(ValueError):
    pass


def user_can_fill_task(
    session: Session, user: User, tenant_id: int, space_id: int, task: SubmissionTask
) -> bool:
    if user.is_superuser:
        return True
    if not has_function_fo_role(user):
        return False
    if task.assignee_user_id == user.id:
        return True
    binding = session.exec(
        select(FoUserFunctionBinding).where(
            FoUserFunctionBinding.tenant_id == tenant_id,
            FoUserFunctionBinding.project_space_id == space_id,
            FoUserFunctionBinding.user_id == user.id,
            FoUserFunctionBinding.business_function_id == task.business_function_id,
            FoUserFunctionBinding.status == "active",
        )
    ).first()
    return binding is not None


def filter_task_patch_fields(
    session: Session,
    user: User,
    tenant_id: int,
    space_id: int,
    task: SubmissionTask,
    fields: dict,
) -> dict:
    if not fields:
        raise TaskPatchValidationError("未提供可更新字段")
    staff = is_staff(user)
    can_fo = user_can_fill_task(session, user, tenant_id, space_id, task)
    allowed: dict = {}
    for key, value in fields.items():
        if key not in ALLOWED_PATCH_KEYS:
            raise TaskPatchValidationError(f"不允许修改字段：{key}")
        if key in STAFF_PATCH_KEYS:
            if not staff:
                raise TaskPatchPermissionError("仅数据安全 FO 或系统管理员可修改审批相关字段")
        elif key in FO_PATCH_KEYS:
            if not can_fo:
                raise TaskPatchPermissionError("仅绑定的功能 FO 可修改填报相关字段")
        elif key in META_PATCH_KEYS:
            if not staff:
                raise TaskPatchPermissionError("仅数据安全 FO 或系统管理员可修改任务基本信息")
        allowed[key] = value
    return allowed


def task_to_frontend(session: Session, task: SubmissionTask) -> dict:
    fn = session.get(BusinessFunction, task.business_function_id)
    function_key = fn.function_key if fn else str(task.business_function_id)
    return {
        "id": task.id,
        "functionId": function_key,
        "business_function_id": task.business_function_id,
        "title": task.title,
        "internalNote": task.internal_note or "",
        "status": task.status,
        "dispatchNote": task.dispatch_note,
        "dispatchedAt": task.dispatched_at.strftime("%Y-%m-%d") if task.dispatched_at else None,
        "createdAt": task.created_at.strftime("%Y-%m-%d") if task.created_at else "",
        "foFillStatus": task.fo_fill_status,
        "foFillContentSummary": task.fo_fill_content_summary or "",
        "foFillFormSnapshot": json.loads(task.fo_fill_form_snapshot_json) if task.fo_fill_form_snapshot_json else None,
        "foFillLifecycleRows": json.loads(task.fo_fill_lifecycle_rows_json) if task.fo_fill_lifecycle_rows_json else None,
        "foCancellationRequested": task.fo_cancellation_requested,
        "foCancellationReason": task.fo_cancellation_reason or "",
        "foCancelApprovalPending": task.fo_cancel_approval_pending,
        "foWorkflowStep": task.fo_workflow_step,
        "foRelevanceConclusion": task.fo_relevance_conclusion,
        "foRelevanceFillRow": json.loads(task.fo_relevance_fill_row_json) if task.fo_relevance_fill_row_json else None,
        "foGovernanceResult": json.loads(task.fo_governance_result_json) if task.fo_governance_result_json else None,
        "auditStatus": task.audit_status,
        "auditComment": task.audit_comment or "",
        "auditedAt": task.audited_at.strftime("%Y-%m-%d %H:%M") if task.audited_at else None,
        "assignee_user_id": task.assignee_user_id,
    }


def resolve_function_id(session: Session, tenant_id: int, space_id: int, function_key: str) -> int | None:
    fn = session.exec(
        select(BusinessFunction).where(
            BusinessFunction.tenant_id == tenant_id,
            BusinessFunction.project_space_id == space_id,
            BusinessFunction.function_key == function_key,
        )
    ).first()
    return fn.id if fn else None


def function_has_active_fo(session: Session, tenant_id: int, space_id: int, function_id: int) -> bool:
    return (
        session.exec(
            select(FoUserFunctionBinding).where(
                FoUserFunctionBinding.tenant_id == tenant_id,
                FoUserFunctionBinding.project_space_id == space_id,
                FoUserFunctionBinding.business_function_id == function_id,
                FoUserFunctionBinding.status == "active",
            )
        ).first()
        is not None
    )


def create_task(
    session: Session,
    *,
    tenant_id: int,
    space_id: int,
    function_key: str,
    title: str,
    internal_note: str = "",
    created_by_user_id: int | None,
) -> SubmissionTask:
    fn_id = resolve_function_id(session, tenant_id, space_id, function_key)
    if not fn_id:
        raise ValueError("业务功能不存在")
    task = SubmissionTask(
        tenant_id=tenant_id,
        project_space_id=space_id,
        business_function_id=fn_id,
        title=title.strip(),
        internal_note=internal_note.strip() or None,
        status="draft",
        created_by_user_id=created_by_user_id,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def dispatch_tasks(
    session: Session, *, tenant_id: int, space_id: int, task_ids: list[int], dispatch_note: str
) -> tuple[int, str]:
    if not dispatch_note.strip():
        return 0, "请填写下发说明。"
    count = 0
    now = datetime.now(timezone.utc)
    for tid in task_ids:
        task = session.get(SubmissionTask, tid)
        if not task or task.tenant_id != tenant_id or task.project_space_id != space_id:
            continue
        if task.status != "draft":
            continue
        if not function_has_active_fo(session, tenant_id, space_id, task.business_function_id):
            fn = session.get(BusinessFunction, task.business_function_id)
            name = fn.name if fn else str(task.business_function_id)
            return count, f"「{name}」尚未绑定功能 FO，无法下发。"
        task.status = "dispatched"
        task.dispatch_note = dispatch_note.strip()
        task.dispatched_at = now
        task.fo_fill_status = "not_started"
        session.add(task)
        count += 1
    if count == 0:
        return 0, "没有可下发的草稿任务。"
    session.commit()
    return count, f"已成功下发 {count} 条任务。"


def patch_task(session: Session, task: SubmissionTask, fields: dict) -> SubmissionTask:
    json_map = {
        "fo_fill_form_snapshot_json": "foFillFormSnapshot",
        "fo_fill_lifecycle_rows_json": "foFillLifecycleRows",
        "fo_relevance_fill_row_json": "foRelevanceFillRow",
        "fo_governance_result_json": "foGovernanceResult",
    }
    simple_map = {
        "fo_fill_status": "foFillStatus",
        "fo_fill_content_summary": "foFillContentSummary",
        "fo_cancellation_requested": "foCancellationRequested",
        "fo_cancellation_reason": "foCancellationReason",
        "fo_cancel_approval_pending": "foCancelApprovalPending",
        "fo_workflow_step": "foWorkflowStep",
        "fo_relevance_conclusion": "foRelevanceConclusion",
        "audit_status": "auditStatus",
        "audit_comment": "auditComment",
        "title": "title",
        "internal_note": "internalNote",
        "status": "status",
        "dispatch_note": "dispatchNote",
    }
    for col, key in simple_map.items():
        if key in fields:
            setattr(task, col, fields[key])
    for col, key in json_map.items():
        if key in fields:
            val = fields[key]
            setattr(task, col, json.dumps(val, ensure_ascii=False) if val is not None else None)
    if "auditedAt" in fields and fields["auditedAt"]:
        task.audited_at = datetime.now(timezone.utc)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
