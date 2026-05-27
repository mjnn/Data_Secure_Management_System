"""将来源空间中「审核已通过」的填报任务复制到目标空间（新建项目时勾选）。"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, select

from app.models import ProjectSpace
from app.models_portal import BusinessFunction, SubmissionTask, SubmissionTaskAssignee

LIFECYCLE_DATA_FIELD_KEY = "data_field"
LIFECYCLE_BUSINESS_FUNCTION_KEY = "business_function"


def _ensure_target_business_function(
    session: Session,
    *,
    src_fn: BusinessFunction,
    target_tenant_id: int,
    target_space_id: int,
    fn_by_key: dict[str, BusinessFunction],
    fn_key_by_target_id: dict[int, str],
) -> BusinessFunction:
    key = src_fn.function_key
    existing = fn_by_key.get(key)
    if existing:
        return existing
    created = BusinessFunction(
        tenant_id=target_tenant_id,
        project_space_id=target_space_id,
        function_key=src_fn.function_key,
        name=src_fn.name,
        description=src_fn.description,
        requires_fo_binding=src_fn.requires_fo_binding,
        sort_order=src_fn.sort_order,
        is_active=src_fn.is_active,
    )
    session.add(created)
    session.flush()
    fn_by_key[key] = created
    fn_key_by_target_id[created.id] = key
    return created


def _remap_lifecycle_rows(
    rows: list[dict[str, Any]] | None,
    fn_key_by_target_id: dict[int, str],
) -> list[dict[str, Any]] | None:
    if not rows:
        return None
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        copied = dict(row)
        bf = copied.get(LIFECYCLE_BUSINESS_FUNCTION_KEY)
        if bf is not None and str(bf).strip():
            key = str(bf).strip()
            if key not in fn_key_by_target_id.values():
                copied[LIFECYCLE_BUSINESS_FUNCTION_KEY] = key
        out.append(copied)
    return out or None


def copy_approved_submission_tasks(
    session: Session,
    *,
    source_tenant_id: int,
    source_space_id: int,
    target_tenant_id: int,
    target_space_id: int,
) -> dict[str, Any]:
    src_space = session.get(ProjectSpace, source_space_id)
    if not src_space or src_space.tenant_id != source_tenant_id:
        return {"ok": False, "message": "来源项目空间不存在"}
    tgt_space = session.get(ProjectSpace, target_space_id)
    if not tgt_space or tgt_space.tenant_id != target_tenant_id:
        return {"ok": False, "message": "目标项目空间不存在"}

    target_fns = session.exec(
        select(BusinessFunction).where(
            BusinessFunction.tenant_id == target_tenant_id,
            BusinessFunction.project_space_id == target_space_id,
        )
    ).all()
    fn_by_key = {f.function_key: f for f in target_fns}
    fn_key_by_target_id = {f.id: f.function_key for f in target_fns}

    source_tasks = session.exec(
        select(SubmissionTask).where(
            SubmissionTask.tenant_id == source_tenant_id,
            SubmissionTask.project_space_id == source_space_id,
            SubmissionTask.audit_status == "approved",
        )
    ).all()

    copied = 0
    skipped: list[dict[str, Any]] = []

    for src in source_tasks:
        src_fn = session.get(BusinessFunction, src.business_function_id)
        if not src_fn:
            skipped.append(
                {
                    "source_task_id": src.id,
                    "title": src.title,
                    "reason": f"来源业务功能不存在（id={src.business_function_id}）",
                }
            )
            continue

        tgt_fn = _ensure_target_business_function(
            session,
            src_fn=src_fn,
            target_tenant_id=target_tenant_id,
            target_space_id=target_space_id,
            fn_by_key=fn_by_key,
            fn_key_by_target_id=fn_key_by_target_id,
        )
        lifecycle = None
        if src.fo_fill_lifecycle_rows_json:
            try:
                raw_rows = json.loads(src.fo_fill_lifecycle_rows_json)
                if isinstance(raw_rows, list):
                    lifecycle = _remap_lifecycle_rows(raw_rows, fn_key_by_target_id)
            except json.JSONDecodeError:
                lifecycle = None

        new_task = SubmissionTask(
            tenant_id=target_tenant_id,
            project_space_id=target_space_id,
            business_function_id=tgt_fn.id,
            title=src.title,
            internal_note=src.internal_note,
            status=src.status,
            dispatch_note=src.dispatch_note,
            dispatched_at=src.dispatched_at,
            created_by_user_id=src.created_by_user_id,
            assignee_user_id=src.assignee_user_id,
            fo_fill_status=src.fo_fill_status,
            fo_fill_content_summary=src.fo_fill_content_summary,
            fo_fill_form_snapshot_json=src.fo_fill_form_snapshot_json,
            fo_fill_lifecycle_rows_json=json.dumps(lifecycle, ensure_ascii=False) if lifecycle else src.fo_fill_lifecycle_rows_json,
            fo_cancellation_requested=src.fo_cancellation_requested,
            fo_cancellation_reason=src.fo_cancellation_reason,
            fo_cancel_approval_pending=False,
            fo_workflow_step=src.fo_workflow_step,
            fo_relevance_conclusion=src.fo_relevance_conclusion,
            fo_relevance_fill_row_json=src.fo_relevance_fill_row_json,
            fo_governance_result_json=src.fo_governance_result_json,
            audit_status=src.audit_status,
            audit_comment=src.audit_comment,
            audited_at=src.audited_at,
        )
        session.add(new_task)
        session.flush()

        assignees = session.exec(
            select(SubmissionTaskAssignee).where(
                SubmissionTaskAssignee.tenant_id == source_tenant_id,
                SubmissionTaskAssignee.submission_task_id == src.id,
            )
        ).all()
        for a in assignees:
            session.add(
                SubmissionTaskAssignee(
                    tenant_id=target_tenant_id,
                    submission_task_id=new_task.id,
                    label=a.label,
                    user_id=a.user_id,
                    fo_fill_status=a.fo_fill_status,
                    fo_fill_content_summary=a.fo_fill_content_summary,
                    fo_fill_form_snapshot_json=a.fo_fill_form_snapshot_json,
                    fo_cancellation_requested=a.fo_cancellation_requested,
                    fo_cancellation_reason=a.fo_cancellation_reason,
                )
            )
        copied += 1

    return {
        "ok": True,
        "message": f"已复制 {copied} 条已审核通过的填报任务。",
        "copied_count": copied,
        "skipped": skipped,
    }
