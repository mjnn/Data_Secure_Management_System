"""门户 Mock 对齐 API + 文档资源（docs/DSMS_DATA_MODEL.md）。"""

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_membership, require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import ProjectSpace, User
from app.models_portal import (
    ApprovalRequest,
    BusinessFunction,
    DocumentResource,
    DocumentTransferJob,
    FoUserFunctionBinding,
    SubmissionTask,
)
from app.schemas import Page
from app.schemas_portal import (
    ApprovalRejectIn,
    ApprovalRequestDetailOut,
    BusinessFunctionOut,
    DocumentExportIn,
    DocumentModuleOut,
    DocumentResourceOut,
    DocumentResourcePatchIn,
    DocumentTransferJobOut,
    FieldCatalogChangeApplyIn,
    FoBindingApplyIn,
    FoBindingSetIn,
    FoBindingsOut,
    SubmissionTaskCreateIn,
    SubmissionTaskDispatchIn,
    SubmissionTaskOut,
    SubmissionTaskPatchIn,
    SubmissionTasksCopyApprovedIn,
)
from app.services.approval_service import (
    APPROVAL_STATUS_PENDING,
    APPROVAL_TYPE_FO_FUNCTION_BINDING,
    approval_to_dict,
    apply_fo_bindings_for_user,
    approve_request,
    create_field_catalog_change_request,
    create_fo_binding_request,
    _resolve_function_ids,
    create_submission_cancel_request,
    create_submission_review_request,
    reject_request,
)
from app.services.submission_task_service import (
    create_task,
    dispatch_tasks,
    function_has_active_fo,
    patch_task,
    task_to_frontend,
)
from app.services.document_registry import get_module_spec, list_modules_dict
from app.services.document_service import (
    build_module_template_xlsx,
    create_document_resource,
    resolve_storage_path,
    run_export_job,
    run_import_job,
)

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-portal"])


def page_limit(limit: int) -> int:
    return min(max(limit, 1), 500)


def _require_staff(user: User) -> User:
    if user.is_superuser or user.platform_role in ("system_admin", "security_fo"):
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅数据安全 FO 或系统管理员可执行该操作")


def _get_space_or_404(session: Session, tenant_id: int, space_id: int) -> ProjectSpace:
    space = session.get(ProjectSpace, space_id)
    if not space or space.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目空间不存在")
    return space


@router.get(
    "/tenants/{tenant_id}/documents/modules",
    response_model=list[DocumentModuleOut],
    description="权限：tenant_member。返回可 Excel 导入/导出的模块注册表。",
)
def list_document_modules(
    tenant_id: int,
    _: User = Depends(require_tenant_member),
):
    return list_modules_dict()


@router.get(
    "/tenants/{tenant_id}/documents/modules/{module_key}/template",
    description="权限：tenant_member。下载指定模块导入模板。",
)
def download_module_template(
    tenant_id: int,
    module_key: str,
    _: User = Depends(require_tenant_member),
):
    spec = get_module_spec(module_key)
    if not spec or not spec.import_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模块不存在或不支持导入模板")
    content = build_module_template_xlsx(module_key)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{spec.template_filename}"'},
    )


@router.get(
    "/tenants/{tenant_id}/documents/resources",
    response_model=Page,
    description="权限：tenant_member。法规文件与导入/导出物列表。",
)
def list_document_resources(
    tenant_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    kind: str | None = None,
    module_key: str | None = None,
    q: str | None = None,
    include_archived: bool = False,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(DocumentResource).where(DocumentResource.tenant_id == tenant_id)
    if not include_archived:
        stmt = stmt.where(DocumentResource.is_archived == False)  # noqa: E712
    if kind:
        stmt = stmt.where(DocumentResource.resource_kind == kind)
    if module_key:
        stmt = stmt.where(DocumentResource.module_key == module_key)
    rows = session.exec(stmt.order_by(DocumentResource.created_at.desc())).all()
    if q:
        q_lower = q.strip().lower()
        rows = [
            r
            for r in rows
            if q_lower in (r.title or "").lower()
            or q_lower in (r.original_file_name or "").lower()
            or q_lower in (r.description or "").lower()
        ]
    total = len(rows)
    page = rows[skip : skip + limit]
    return Page(total=total, items=[DocumentResourceOut.model_validate(r, from_attributes=True) for r in page])


@router.post(
    "/tenants/{tenant_id}/documents/resources",
    response_model=DocumentResourceOut,
    description="权限：security_fo / 超管。上传法规文件或其它文档。",
)
def upload_document_resource(
    tenant_id: int,
    title: str = Query(..., min_length=1),
    resource_kind: str = Query(default="regulation"),
    description: str | None = None,
    project_space_id: int | None = None,
    module_key: str | None = None,
    tags_json: str | None = None,
    regulation_meta_json: str | None = None,
    file: UploadFile = File(...),
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _require_staff(current_user)
    if project_space_id is not None:
        _get_space_or_404(session, tenant_id, project_space_id)
    content = file.file.read()
    try:
        row = create_document_resource(
            session,
            tenant_id=tenant_id,
            project_space_id=project_space_id,
            resource_kind=resource_kind,
            module_key=module_key,
            title=title,
            description=description,
            original_file_name=file.filename or "upload.bin",
            mime_type=file.content_type or "application/octet-stream",
            content=content,
            uploaded_by_user_id=current_user.id,
            tags_json=tags_json,
            regulation_meta_json=regulation_meta_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return DocumentResourceOut.model_validate(row, from_attributes=True)


@router.patch(
    "/tenants/{tenant_id}/documents/resources/{resource_id}",
    response_model=DocumentResourceOut,
    description="权限：security_fo / 超管。更新标题、归档等。",
)
def patch_document_resource(
    tenant_id: int,
    resource_id: int,
    payload: DocumentResourcePatchIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _require_staff(current_user)
    row = session.get(DocumentResource, resource_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    session.add(row)
    session.commit()
    session.refresh(row)
    return DocumentResourceOut.model_validate(row, from_attributes=True)


@router.get(
    "/tenants/{tenant_id}/documents/resources/{resource_id}/download",
    description="权限：tenant_member。下载文档文件。",
)
def download_document_resource(
    tenant_id: int,
    resource_id: int,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    row = session.get(DocumentResource, resource_id)
    if not row or row.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    path = resolve_storage_path(tenant_id, row.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件已丢失")
    data = path.read_bytes()
    return StreamingResponse(
        BytesIO(data),
        media_type=row.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{row.original_file_name}"'},
    )


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/documents/export",
    response_model=DocumentTransferJobOut,
    description="权限：tenant_member。发起 Excel 导出作业（同步执行）。",
)
def create_export_job(
    tenant_id: int,
    space_id: int,
    payload: DocumentExportIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _get_space_or_404(session, tenant_id, space_id)
    spec = get_module_spec(payload.module_key)
    if not spec or not spec.export_enabled:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该模块不支持导出")
    job = DocumentTransferJob(
        tenant_id=tenant_id,
        project_space_id=space_id,
        direction="export",
        module_key=payload.module_key,
        status="pending",
        created_by_user_id=current_user.id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    job = run_export_job(session, job)
    return DocumentTransferJobOut.model_validate(job, from_attributes=True)


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/documents/import",
    response_model=DocumentTransferJobOut,
    description="权限：security_fo / 超管。上传 xlsx 并执行导入作业。",
)
def create_import_job(
    tenant_id: int,
    space_id: int,
    module_key: str = Query(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _require_staff(current_user)
    _get_space_or_404(session, tenant_id, space_id)
    spec = get_module_spec(module_key)
    if not spec or not spec.import_enabled:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该模块不支持导入")
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="仅支持 .xlsx 文件")
    content = file.file.read()
    source = create_document_resource(
        session,
        tenant_id=tenant_id,
        project_space_id=space_id,
        resource_kind="import_upload",
        module_key=module_key,
        title=f"{module_key} 导入源文件",
        description=None,
        original_file_name=file.filename or "import.xlsx",
        mime_type=file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=content,
        uploaded_by_user_id=current_user.id,
    )
    job = DocumentTransferJob(
        tenant_id=tenant_id,
        project_space_id=space_id,
        direction="import",
        module_key=module_key,
        status="pending",
        source_resource_id=source.id,
        created_by_user_id=current_user.id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    job = run_import_job(session, job, content)
    return DocumentTransferJobOut.model_validate(job, from_attributes=True)


@router.get(
    "/tenants/{tenant_id}/documents/jobs",
    response_model=Page,
    description="权限：tenant_member。导入/导出作业列表。",
)
def list_document_jobs(
    tenant_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    direction: str | None = None,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(DocumentTransferJob).where(DocumentTransferJob.tenant_id == tenant_id)
    if direction:
        stmt = stmt.where(DocumentTransferJob.direction == direction)
    rows = session.exec(stmt.order_by(DocumentTransferJob.created_at.desc())).all()
    total = len(rows)
    page = rows[skip : skip + limit]
    return Page(total=total, items=[DocumentTransferJobOut.model_validate(r, from_attributes=True) for r in page])


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
    _get_space_or_404(session, tenant_id, space_id)
    limit = page_limit(limit)
    rows = session.exec(
        select(SubmissionTask)
        .where(SubmissionTask.tenant_id == tenant_id, SubmissionTask.project_space_id == space_id)
        .order_by(SubmissionTask.created_at.desc())
    ).all()
    fn_rows = session.exec(
        select(BusinessFunction).where(
            BusinessFunction.tenant_id == tenant_id,
            BusinessFunction.project_space_id == space_id,
        )
    ).all()
    fn_by_id = {f.id: f for f in fn_rows}
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
    _get_space_or_404(session, tenant_id, space_id)
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
    _get_space_or_404(session, tenant_id, space_id)
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
    _get_space_or_404(session, tenant_id, space_id)
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
    _require_staff(current_user)
    _get_space_or_404(session, tenant_id, space_id)
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
    description="权限：tenant_member。更新任务（含 FO 工作流字段）。",
)
def patch_submission_task(
    tenant_id: int,
    space_id: int,
    task_id: int,
    payload: SubmissionTaskPatchIn,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _get_space_or_404(session, tenant_id, space_id)
    task = session.get(SubmissionTask, task_id)
    if not task or task.tenant_id != tenant_id or task.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    task = patch_task(session, task, payload.fields)
    marking_approved = payload.fields.get("auditStatus") == "approved"
    if (
        payload.fields.get("foFillStatus") == "submitted"
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
    _require_staff(current_user)
    _get_space_or_404(session, tenant_id, space_id)
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

    _get_space_or_404(session, tenant_id, space_id)
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
    _get_space_or_404(session, tenant_id, space_id)
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


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/fo-function-bindings/me",
    description="权限：tenant_member。当前用户生效的业务功能绑定。",
)
def get_my_fo_bindings(
    tenant_id: int,
    space_id: int,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _get_space_or_404(session, tenant_id, space_id)
    bindings = session.exec(
        select(FoUserFunctionBinding).where(
            FoUserFunctionBinding.tenant_id == tenant_id,
            FoUserFunctionBinding.project_space_id == space_id,
            FoUserFunctionBinding.user_id == current_user.id,
            FoUserFunctionBinding.status == "active",
        )
    ).all()
    fn_rows = session.exec(
        select(BusinessFunction).where(
            BusinessFunction.tenant_id == tenant_id,
            BusinessFunction.project_space_id == space_id,
        )
    ).all()
    id_to_key = {f.id: f.function_key for f in fn_rows}
    keys = [id_to_key.get(b.business_function_id) for b in bindings if id_to_key.get(b.business_function_id)]
    pending = session.exec(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.project_space_id == space_id,
            ApprovalRequest.request_type == APPROVAL_TYPE_FO_FUNCTION_BINDING,
            ApprovalRequest.status == APPROVAL_STATUS_PENDING,
            ApprovalRequest.requester_user_id == current_user.id,
        )
    ).first()
    return {"function_keys": keys, "has_pending_binding_request": pending is not None}


def _fo_bindings_payload(
    session: Session, tenant_id: int, space_id: int, user_id: int
) -> FoBindingsOut:
    bindings = session.exec(
        select(FoUserFunctionBinding).where(
            FoUserFunctionBinding.tenant_id == tenant_id,
            FoUserFunctionBinding.project_space_id == space_id,
            FoUserFunctionBinding.user_id == user_id,
            FoUserFunctionBinding.status == "active",
        )
    ).all()
    fn_rows = session.exec(
        select(BusinessFunction).where(
            BusinessFunction.tenant_id == tenant_id,
            BusinessFunction.project_space_id == space_id,
        )
    ).all()
    id_to_key = {f.id: f.function_key for f in fn_rows}
    keys = [id_to_key.get(b.business_function_id) for b in bindings if id_to_key.get(b.business_function_id)]
    pending = session.exec(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.project_space_id == space_id,
            ApprovalRequest.request_type == APPROVAL_TYPE_FO_FUNCTION_BINDING,
            ApprovalRequest.status == APPROVAL_STATUS_PENDING,
            ApprovalRequest.requester_user_id == user_id,
        )
    ).first()
    return FoBindingsOut(function_keys=keys, has_pending_binding_request=pending is not None)


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/fo-function-bindings/users/{user_id}",
    response_model=FoBindingsOut,
    description="权限：tenant_admin+。查询指定用户的业务功能绑定。",
)
def get_user_fo_bindings(
    tenant_id: int,
    space_id: int,
    user_id: int,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    _get_space_or_404(session, tenant_id, space_id)
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return _fo_bindings_payload(session, tenant_id, space_id, user_id)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/fo-function-bindings/users/{user_id}",
    response_model=FoBindingsOut,
    description="权限：tenant_admin+。管理员直接设置功能 FO 的业务功能绑定（不经审批）。",
)
def put_user_fo_bindings(
    tenant_id: int,
    space_id: int,
    user_id: int,
    payload: FoBindingSetIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    _get_space_or_404(session, tenant_id, space_id)
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.platform_role != "function_fo" and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="仅可为功能 FO 用户设置业务功能绑定")
    desired_ids = _resolve_function_ids(session, tenant_id, space_id, payload.function_keys or [])
    apply_fo_bindings_for_user(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        user_id=user_id,
        desired_function_ids=desired_ids,
        approved_via_request_id=None,
    )
    session.commit()
    return _fo_bindings_payload(session, tenant_id, space_id, user_id)


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/fo-function-binding-requests",
    description="权限：function_fo。提交绑定变更申请。",
)
def post_fo_binding_request(
    tenant_id: int,
    space_id: int,
    payload: FoBindingApplyIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _get_space_or_404(session, tenant_id, space_id)
    req, msg = create_fo_binding_request(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        requester=current_user,
        desired_function_keys=payload.desired_function_keys,
        reason=payload.reason or "",
    )
    if req is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    return {"message": msg}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/field-catalog-change-requests",
    description="权限：function_fo。字段目录增删申请。",
)
def post_field_catalog_change(
    tenant_id: int,
    space_id: int,
    payload: FieldCatalogChangeApplyIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _get_space_or_404(session, tenant_id, space_id)
    _, msg = create_field_catalog_change_request(
        session,
        tenant_id=tenant_id,
        space_id=space_id,
        requester=current_user,
        request_type=payload.request_type,
        proposed_label=payload.proposed_label,
        proposed_description=payload.proposed_description or "",
        catalog_entry_id=payload.catalog_entry_id,
    )
    return {"message": msg}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/approval-requests/{request_id}/approve",
    description="权限：security_fo / 超管。审批通过。",
)
def post_approve_request(
    tenant_id: int,
    space_id: int,
    request_id: int,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _require_staff(current_user)
    _get_space_or_404(session, tenant_id, space_id)
    req = session.get(ApprovalRequest, request_id)
    if not req or req.tenant_id != tenant_id or req.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")
    ok, msg = approve_request(session, request_id, current_user)
    if not ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    return {"message": msg}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/approval-requests/{request_id}/reject",
    description="权限：security_fo / 超管。审批驳回。",
)
def post_reject_request(
    tenant_id: int,
    space_id: int,
    request_id: int,
    payload: ApprovalRejectIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _require_staff(current_user)
    _get_space_or_404(session, tenant_id, space_id)
    req = session.get(ApprovalRequest, request_id)
    if not req or req.tenant_id != tenant_id or req.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")
    ok, msg = reject_request(session, request_id, current_user, payload.reason)
    if not ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    return {"message": msg}


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/approval-requests/pending-count",
    description="权限：tenant_member。待审批数量（数据安全 FO 侧栏红点）。",
)
def get_pending_approval_count(
    tenant_id: int,
    space_id: int,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    _get_space_or_404(session, tenant_id, space_id)
    if not (current_user.is_superuser or current_user.platform_role in ("system_admin", "security_fo")):
        return {"count": 0}
    rows = session.exec(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.project_space_id == space_id,
            ApprovalRequest.status == APPROVAL_STATUS_PENDING,
        )
    ).all()
    return {"count": len(rows)}
