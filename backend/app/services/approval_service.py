"""审批中心业务逻辑（对齐 frontend approvalRequestsMock.js）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import FieldCatalogEntry, User
from app.models_portal import (
    ApprovalRequest,
    BusinessFunction,
    FieldCatalogChangeRequest,
    FoUserFunctionBinding,
    SubmissionTask,
)

APPROVAL_STATUS_PENDING = "pending"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_REJECTED = "rejected"

APPROVAL_TYPE_FO_FUNCTION_BINDING = "fo_function_binding"
APPROVAL_TYPE_FIELD_CATALOG_CREATE = "field_catalog_create"
APPROVAL_TYPE_FIELD_CATALOG_DELETE = "field_catalog_delete"
APPROVAL_TYPE_SUBMISSION_CANCEL = "submission_fill_cancel"
APPROVAL_TYPE_SUBMISSION_REVIEW = "submission_fill_review"


def user_display(user: User | None) -> str:
    if not user:
        return ""
    return user.full_name or user.username


def approval_to_dict(req: ApprovalRequest, session: Session) -> dict:
    requester = session.get(User, req.requester_user_id)
    reviewer = session.get(User, req.reviewer_user_id) if req.reviewer_user_id else None
    try:
        payload = json.loads(req.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {
        "id": req.id,
        "request_type": req.request_type,
        "type": req.request_type,
        "status": req.status,
        "title": req.title,
        "payload_json": req.payload_json,
        "payload": payload,
        "requester_user_id": req.requester_user_id,
        "reviewer_user_id": req.reviewer_user_id,
        "requestedBy": user_display(requester),
        "reviewedBy": user_display(reviewer),
        "reject_reason": req.reject_reason,
        "rejectReason": req.reject_reason or "",
        "requested_at": req.requested_at,
        "requestedAt": req.requested_at.strftime("%Y-%m-%d %H:%M") if req.requested_at else "",
        "reviewed_at": req.reviewed_at,
        "reviewedAt": req.reviewed_at.strftime("%Y-%m-%d %H:%M") if req.reviewed_at else "",
    }


def _resolve_function_ids(session: Session, tenant_id: int, space_id: int, keys_or_ids: list) -> list[int]:
    ids: list[int] = []
    for raw in keys_or_ids:
        if isinstance(raw, int) or (isinstance(raw, str) and str(raw).isdigit()):
            fid = int(raw)
            fn = session.get(BusinessFunction, fid)
            if fn and fn.tenant_id == tenant_id and fn.project_space_id == space_id and fn.id:
                ids.append(fn.id)
            continue
        fn = session.exec(
            select(BusinessFunction).where(
                BusinessFunction.tenant_id == tenant_id,
                BusinessFunction.project_space_id == space_id,
                BusinessFunction.function_key == str(raw),
            )
        ).first()
        if fn and fn.id:
            ids.append(fn.id)
    return ids


def create_fo_binding_request(
    session: Session,
    *,
    tenant_id: int,
    space_id: int,
    requester: User,
    desired_function_keys: list[str],
    reason: str = "",
) -> tuple[ApprovalRequest | None, str]:
    pending = session.exec(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.project_space_id == space_id,
            ApprovalRequest.request_type == APPROVAL_TYPE_FO_FUNCTION_BINDING,
            ApprovalRequest.status == APPROVAL_STATUS_PENDING,
            ApprovalRequest.requester_user_id == requester.id,
        )
    ).first()
    if pending:
        return None, "已有待审批的绑定变更申请，请等待处理。"

    desired_ids = _resolve_function_ids(session, tenant_id, space_id, desired_function_keys)
    if not desired_ids:
        return None, "请至少选择一项有效的业务功能。"

    active_bindings = session.exec(
        select(FoUserFunctionBinding).where(
            FoUserFunctionBinding.tenant_id == tenant_id,
            FoUserFunctionBinding.project_space_id == space_id,
            FoUserFunctionBinding.user_id == requester.id,
            FoUserFunctionBinding.status == "active",
        )
    ).all()
    previous_ids = [b.business_function_id for b in active_bindings]

    payload = {
        "desired_function_ids": desired_ids,
        "desired_function_keys": desired_function_keys,
        "previous_function_ids": previous_ids,
        "reason": reason.strip(),
    }
    req = ApprovalRequest(
        tenant_id=tenant_id,
        project_space_id=space_id,
        request_type=APPROVAL_TYPE_FO_FUNCTION_BINDING,
        status=APPROVAL_STATUS_PENDING,
        title="业务功能绑定变更申请",
        payload_json=json.dumps(payload, ensure_ascii=False),
        requester_user_id=requester.id,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return req, "已提交绑定变更申请，请等待数据安全 FO 审批。"


def create_field_catalog_change_request(
    session: Session,
    *,
    tenant_id: int,
    space_id: int,
    requester: User,
    request_type: str,
    proposed_label: str,
    proposed_description: str = "",
    catalog_entry_id: int | None = None,
) -> tuple[ApprovalRequest | None, str]:
    if request_type not in ("create", "delete"):
        return None, "无效申请类型。"
    change = FieldCatalogChangeRequest(
        tenant_id=tenant_id,
        project_space_id=space_id,
        request_type=request_type,
        catalog_entry_id=catalog_entry_id,
        proposed_label=proposed_label.strip(),
        proposed_description=proposed_description.strip() or None,
        status=APPROVAL_STATUS_PENDING,
        requester_user_id=requester.id,
    )
    session.add(change)
    session.flush()

    approval_type = (
        APPROVAL_TYPE_FIELD_CATALOG_CREATE if request_type == "create" else APPROVAL_TYPE_FIELD_CATALOG_DELETE
    )
    title = (
        f"申请新增数据字段：{proposed_label}"
        if request_type == "create"
        else f"申请删除数据字段：{proposed_label}"
    )
    payload = {
        "change_request_id": change.id,
        "catalog_entry_id": catalog_entry_id,
        "proposed_label": proposed_label,
        "proposed_description": proposed_description,
    }
    req = ApprovalRequest(
        tenant_id=tenant_id,
        project_space_id=space_id,
        request_type=approval_type,
        status=APPROVAL_STATUS_PENDING,
        title=title,
        payload_json=json.dumps(payload, ensure_ascii=False),
        requester_user_id=requester.id,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return req, "申请已提交。"


def create_submission_cancel_request(
    session: Session,
    *,
    tenant_id: int,
    space_id: int,
    requester: User,
    task_id: int,
    reason: str,
) -> tuple[ApprovalRequest | None, str]:
    task = session.get(SubmissionTask, task_id)
    if not task or task.tenant_id != tenant_id or task.project_space_id != space_id:
        return None, "未找到填报任务。"
    existing = session.exec(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.project_space_id == space_id,
            ApprovalRequest.request_type == APPROVAL_TYPE_SUBMISSION_CANCEL,
            ApprovalRequest.status == APPROVAL_STATUS_PENDING,
        )
    ).all()
    for r in existing:
        try:
            p = json.loads(r.payload_json or "{}")
        except json.JSONDecodeError:
            p = {}
        if p.get("task_id") == task_id:
            return None, "该任务已有待审批的取消申请。"

    fn = session.get(BusinessFunction, task.business_function_id)
    payload = {"task_id": task_id, "function_id": fn.function_key if fn else task.business_function_id, "reason": reason}
    req = ApprovalRequest(
        tenant_id=tenant_id,
        project_space_id=space_id,
        request_type=APPROVAL_TYPE_SUBMISSION_CANCEL,
        status=APPROVAL_STATUS_PENDING,
        title=f"取消填报：{task.title}",
        payload_json=json.dumps(payload, ensure_ascii=False),
        requester_user_id=requester.id,
    )
    session.add(req)
    task.fo_cancel_approval_pending = True
    task.fo_cancellation_reason = reason.strip()
    session.add(task)
    session.commit()
    session.refresh(req)
    return req, "已提交取消申请，请等待数据安全 FO 审批。"


def create_submission_review_request(session: Session, *, task: SubmissionTask) -> None:
    existing = session.exec(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == task.tenant_id,
            ApprovalRequest.project_space_id == task.project_space_id,
            ApprovalRequest.request_type == APPROVAL_TYPE_SUBMISSION_REVIEW,
            ApprovalRequest.status == APPROVAL_STATUS_PENDING,
        )
    ).all()
    for r in existing:
        try:
            p = json.loads(r.payload_json or "{}")
        except json.JSONDecodeError:
            p = {}
        if p.get("task_id") == task.id:
            task.audit_status = "pending"
            session.add(task)
            session.commit()
            return

    fn = session.get(BusinessFunction, task.business_function_id)
    fn_label = fn.name if fn else str(task.business_function_id)
    payload = {"task_id": task.id, "function_id": fn.function_key if fn else task.business_function_id}
    req = ApprovalRequest(
        tenant_id=task.tenant_id,
        project_space_id=task.project_space_id,
        request_type=APPROVAL_TYPE_SUBMISSION_REVIEW,
        status=APPROVAL_STATUS_PENDING,
        title=f"填报审核：{task.title}（{fn_label}）",
        payload_json=json.dumps(payload, ensure_ascii=False),
        requester_user_id=task.assignee_user_id or task.created_by_user_id or 0,
    )
    session.add(req)
    task.audit_status = "pending"
    session.add(task)
    session.commit()


def apply_fo_bindings_for_user(
    session: Session,
    *,
    tenant_id: int,
    space_id: int,
    user_id: int,
    desired_function_ids: list[int],
    approved_via_request_id: int | None = None,
) -> None:
    bindings = session.exec(
        select(FoUserFunctionBinding).where(
            FoUserFunctionBinding.tenant_id == tenant_id,
            FoUserFunctionBinding.project_space_id == space_id,
            FoUserFunctionBinding.user_id == user_id,
        )
    ).all()
    desired_set = set(desired_function_ids)
    for b in bindings:
        if b.business_function_id in desired_set:
            b.status = "active"
            b.approved_via_request_id = approved_via_request_id
            session.add(b)
            desired_set.discard(b.business_function_id)
        else:
            session.delete(b)
    for fid in desired_set:
        session.add(
            FoUserFunctionBinding(
                tenant_id=tenant_id,
                project_space_id=space_id,
                user_id=user_id,
                business_function_id=fid,
                status="active",
                approved_via_request_id=approved_via_request_id,
            )
        )


def _apply_fo_binding(session: Session, req: ApprovalRequest, payload: dict) -> str:
    desired_ids = payload.get("desired_function_ids") or []
    apply_fo_bindings_for_user(
        session,
        tenant_id=req.tenant_id,
        space_id=req.project_space_id,
        user_id=req.requester_user_id,
        desired_function_ids=desired_ids,
        approved_via_request_id=req.id,
    )
    return "已通过，业务功能绑定已更新。"


def _apply_catalog(session: Session, req: ApprovalRequest, payload: dict) -> str:
    change_id = payload.get("change_request_id")
    change = session.get(FieldCatalogChangeRequest, change_id) if change_id else None
    if not change or change.status != APPROVAL_STATUS_PENDING:
        return "未找到待处理的数据字段申请。"
    if req.request_type == APPROVAL_TYPE_FIELD_CATALOG_CREATE:
        lab = change.proposed_label.strip()
        dup = session.exec(
            select(FieldCatalogEntry).where(
                FieldCatalogEntry.tenant_id == req.tenant_id,
                FieldCatalogEntry.project_space_id == req.project_space_id,
                FieldCatalogEntry.field_name == lab,
            )
        ).first()
        if dup:
            return "目录中已存在同名字段，无法通过。"
        key = lab.lower().replace(" ", "_")[:64]
        session.add(
            FieldCatalogEntry(
                tenant_id=req.tenant_id,
                project_space_id=req.project_space_id,
                field_name=lab,
                description=change.proposed_description,
                identifier_key=key,
            )
        )
    else:
        entry = session.get(FieldCatalogEntry, change.catalog_entry_id) if change.catalog_entry_id else None
        if not entry:
            return "目录项已不存在。"
        session.delete(entry)
    change.status = APPROVAL_STATUS_APPROVED
    change.reviewed_at = datetime.now(timezone.utc)
    session.add(change)
    return ""


def approve_request(session: Session, request_id: int, reviewer: User) -> tuple[bool, str]:
    req = session.get(ApprovalRequest, request_id)
    if not req:
        return False, "未找到申请。"
    if req.status != APPROVAL_STATUS_PENDING:
        return False, "该申请已处理。"
    try:
        payload = json.loads(req.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}

    msg = ""
    if req.request_type == APPROVAL_TYPE_FO_FUNCTION_BINDING:
        msg = _apply_fo_binding(session, req, payload)
    elif req.request_type in (APPROVAL_TYPE_FIELD_CATALOG_CREATE, APPROVAL_TYPE_FIELD_CATALOG_DELETE):
        err = _apply_catalog(session, req, payload)
        if err:
            return False, err
        msg = "数据字段申请已通过。"
    elif req.request_type == APPROVAL_TYPE_SUBMISSION_CANCEL:
        task = session.get(SubmissionTask, payload.get("task_id"))
        if not task:
            return False, "未找到填报任务。"
        task.fo_fill_status = "cancelled"
        task.fo_cancel_approval_pending = False
        task.fo_cancellation_requested = True
        task.fo_fill_content_summary = f"取消申请已通过：{payload.get('reason', '')}"
        session.add(task)
        msg = "已通过，任务已取消。"
    elif req.request_type == APPROVAL_TYPE_SUBMISSION_REVIEW:
        task = session.get(SubmissionTask, payload.get("task_id"))
        if not task:
            return False, "未找到填报任务。"
        task.audit_status = "approved"
        task.audit_comment = "审批中心审核通过。"
        task.audited_at = datetime.now(timezone.utc)
        session.add(task)
        msg = "填报审核已通过。"
    else:
        return False, "未知申请类型。"

    req.status = APPROVAL_STATUS_APPROVED
    req.reviewer_user_id = reviewer.id
    req.reviewed_at = datetime.now(timezone.utc)
    session.add(req)
    session.commit()
    return True, msg or "已通过。"


def reject_request(session: Session, request_id: int, reviewer: User, reason: str) -> tuple[bool, str]:
    req = session.get(ApprovalRequest, request_id)
    if not req:
        return False, "未找到申请。"
    if req.status != APPROVAL_STATUS_PENDING:
        return False, "该申请已处理。"
    try:
        payload = json.loads(req.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}

    if req.request_type in (APPROVAL_TYPE_FIELD_CATALOG_CREATE, APPROVAL_TYPE_FIELD_CATALOG_DELETE):
        change = session.get(FieldCatalogChangeRequest, payload.get("change_request_id"))
        if change and change.status == APPROVAL_STATUS_PENDING:
            change.status = APPROVAL_STATUS_REJECTED
            change.reject_reason = reason
            change.reviewed_at = datetime.now(timezone.utc)
            session.add(change)
    elif req.request_type == APPROVAL_TYPE_SUBMISSION_CANCEL:
        task = session.get(SubmissionTask, payload.get("task_id"))
        if task:
            task.fo_cancel_approval_pending = False
            task.fo_cancellation_requested = False
            session.add(task)
    elif req.request_type == APPROVAL_TYPE_SUBMISSION_REVIEW:
        task = session.get(SubmissionTask, payload.get("task_id"))
        if task:
            task.audit_status = "returned"
            task.audit_comment = reason or "审批中心退回。"
            task.audited_at = datetime.now(timezone.utc)
            task.fo_fill_status = "draft"
            session.add(task)

    req.status = APPROVAL_STATUS_REJECTED
    req.reviewer_user_id = reviewer.id
    req.reject_reason = reason.strip()
    req.reviewed_at = datetime.now(timezone.utc)
    session.add(req)
    session.commit()
    return True, "已驳回。"
