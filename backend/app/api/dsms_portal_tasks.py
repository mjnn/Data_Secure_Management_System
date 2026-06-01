"""门户填报任务与业务功能。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.dsms_auth import require_function_fo, require_staff
from app.api.dsms_helpers import get_space_or_404, page_limit
from app.core.deps import get_current_user, get_membership, require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import User
from app.models_portal import ApprovalRequest, BusinessFunction, SubmissionTask
from app.schemas import Page
from app.schemas_portal import (
    BusinessFunctionOut,
    SubmissionTaskCreateIn,
    SubmissionTaskDispatchIn,
    SubmissionTaskPatchIn,
    SubmissionTasksCopyApprovedIn,
)
from app.services.approval_service import approval_to_dict, create_submission_cancel_request, create_submission_review_request
from app.services.submission_task_service import (
    TaskPatchPermissionError,
    TaskPatchValidationError,
    create_task,
    dispatch_tasks,
    filter_task_patch_fields,
    function_has_active_fo,
    patch_task,
    task_to_frontend,
)

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-portal-tasks"])


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/submission-tasks",
    response_model=Page,
    description="权限：tenant_member。填报任务列表（对齐前端 mock）。",
)
def list_submission_tasks(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    limit = page_limit(limit)
    rows = session.exec(
        select(SubmissionTask)
        .where(SubmissionTask.tenant_id == tenant_id, SubmissionTask.project_space_id == space_id)
        .order_by(SubmissionTask.created_at.desc())
    ).all()
    items = [task_to_frontend(session, t) for t in rows[skip : skip + limit]]
    return Page(total=len(rows), items=items)


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/approval-requests",
    response_model=Page,
    description="权限：tenant_member。审批中心列表。",
)
def list_approval_requests(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    limit = page_limit(limit)
    rows = session.exec(
        select(ApprovalRequest)
        .where(ApprovalRequest.tenant_id == tenant_id, ApprovalRequest.project_space_id == space_id)
        .order_by(ApprovalRequest.requested_at.desc())
    ).all()
    if status_filter:
        rows = [r for r in rows if r.status == status_filter]
    if q:
        q_lower = q.strip().lower()
        rows = [
            r
            for r in rows
            if q_lower in r.title.lower()
            or q_lower in r.request_type.lower()
            or q_lower in (r.payload_json or "").lower()
        ]
    total = len(rows)
    page = rows[skip : skip + limit]
    return Page(total=total, items=[approval_to_dict(r, session) for r in page])


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/business-functions",
    response_model=list[BusinessFunctionOut],
    description="权限：tenant_member。业务功能选项（对齐 MOCK_SUBMISSION_FUNCTIONS）。",
)
def list_business_functions(
    tenant_id: int,
    space_id: int,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    rows = session.exec(
        select(BusinessFunction)
        .where(
            BusinessFunction.tenant_id == tenant_id,
            BusinessFunction.project_space_id == space_id,
            BusinessFunction.is_active == True,  # noqa: E712
        )
        .order_by(BusinessFunction.sort_order)
    ).all()
    return [
        BusinessFunctionOut(
            id=r.id,
            function_key=r.function_key,
            name=r.name,
            description=r.description,
            requires_fo_binding=r.requires_fo_binding,
            has_active_fo_binding=function_has_active_fo(session, tenant_id, space_id, r.id),
            sort_order=r.sort_order,
            is_active=r.is_active,
        )
        for r in rows
    ]


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/submission-tasks/{task_id}",
    description="权限：tenant_member。填报任务详情。",
)
def get_submission_task(
    tenant_id: int,
    space_id: int,
    task_id: int,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    task = session.get(SubmissionTask, task_id)
    if not task or task.tenant_id != tenant_id or task.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task_to_frontend(session, task)


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/submission-tasks",
    description="权限：security_fo / 超管。新建草稿任务。",
)
def post_submission_task(
    tenant_id: int,
    space_id: int,
    payload: SubmissionTaskCreateIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    require_staff(current_user)
    get_space_or_404(session, tenant_id, space_id)
    try:
        task = create_task(
            session,
            tenant_id=tenant_id,
            space_id=space_id,
            function_key=payload.function_key,
            title=payload.title,
            internal_note=payload.internal_note or "",
            created_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return task_to_frontend(session, task)


@router.patch(
    "/tenants/{tenant_id}/spaces/{space_id}/submission-tasks/{task_id}",
    description="权限：tenant_member。FO 填报字段限 function_fo；审批字段限 security_fo / 超管。",
)
def patch_submission_task(
    tenant_id: int,
    space_id: int,
    task_id: int,
    payload: SubmissionTaskPatchIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    task = session.get(SubmissionTask, task_id)
    if not task or task.tenant_id != tenant_id or task.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    try:
        filtered_fields = filter_task_patch_fields(
            session, current_user, tenant_id, space_id, task, payload.fields
        )
    except TaskPatchPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except TaskPatchValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    task = patch_task(session, task, filtered_fields)
    marking_approved = filtered_fields.get("auditStatus") == "approved"
    if (
        filtered_fields.get("foFillStatus") == "submitted"
        and task.audit_status != "approved"
        and not marking_approved
    ):
        create_submission_review_request(session, task=task)
    return task_to_frontend(session, task)


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/submission-tasks/dispatch",
    description="权限：security_fo / 超管。批量下发草稿任务。",
)
def post_dispatch_tasks(
    tenant_id: int,
    space_id: int,
    payload: SubmissionTaskDispatchIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    require_staff(current_user)
    get_space_or_404(session, tenant_id, space_id)
    count, msg = dispatch_tasks(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        task_ids=payload.task_ids,
        dispatch_note=payload.dispatch_note,
    )
    if count == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    return {"dispatched_count": count, "message": msg}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/submission-tasks/copy-approved-from",
    description="权限：tenant_admin（目标项目）或 super_admin。复制来源空间中 audit_status=approved 的填报任务到本空间。",
)
def post_copy_approved_submission_tasks(
    tenant_id: int,
    space_id: int,
    payload: SubmissionTasksCopyApprovedIn,
    user: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    from app.services.config_service import governance_log
    from app.services.submission_task_copy_service import copy_approved_submission_tasks

    get_space_or_404(session, tenant_id, space_id)
    if not user.is_superuser:
        if not get_membership(session, payload.source_tenant_id, user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权读取来源项目的填报数据")

    result = copy_approved_submission_tasks(
        session,
        source_tenant_id=payload.source_tenant_id,
        source_space_id=payload.source_project_space_id,
        target_tenant_id=tenant_id,
        target_space_id=space_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))

    governance_log(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user.id,
        behavior_key="dsms-submission-tasks-copy-approved",
        resource_type="submission_task",
        resource_id=None,
        summary=str(result.get("message") or ""),
        detail={
            "source_tenant_id": payload.source_tenant_id,
            "source_project_space_id": payload.source_project_space_id,
            "copied_count": result.get("copied_count", 0),
            "skipped": result.get("skipped", []),
        },
    )
    session.commit()
    return {**result, "behavior_key": "dsms-submission-tasks-copy-approved"}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/submission-tasks/{task_id}/cancel-request",
    description="权限：function_fo。提交取消填报申请。",
)
def post_cancel_request(
    tenant_id: int,
    space_id: int,
    task_id: int,
    reason: str = Query(..., min_length=1),
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    require_function_fo(current_user)
    get_space_or_404(session, tenant_id, space_id)
    req, msg = create_submission_cancel_request(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        requester=current_user,
        task_id=task_id,
        reason=reason,
    )
    if req is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    return {"message": msg}
