"""门户文档模块、资源与导入/导出作业。"""

from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.api.dsms_auth import require_staff
from app.api.dsms_helpers import get_space_or_404, page_limit
from app.core.deps import get_current_user, require_tenant_member
from app.core.database import get_session
from app.core.upload_utils import read_upload_with_limit, safe_content_disposition_filename
from app.models import User
from app.models_portal import DocumentResource, DocumentTransferJob
from app.schemas import Page
from app.schemas_portal import (
    DocumentExportIn,
    DocumentModuleOut,
    DocumentResourceOut,
    DocumentResourcePatchIn,
    DocumentTransferJobOut,
)
from app.services.document_registry import get_module_spec, list_modules_dict
from app.services.document_service import (
    build_module_template_xlsx,
    create_document_resource,
    resolve_storage_path,
    run_export_job,
    run_import_job,
)

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-portal-documents"])


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
    require_staff(current_user)
    if project_space_id is not None:
        get_space_or_404(session, tenant_id, project_space_id)
    try:
        content = read_upload_with_limit(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
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
    require_staff(current_user)
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
    filename = safe_content_disposition_filename(row.original_file_name, "document")
    return StreamingResponse(
        BytesIO(data),
        media_type=row.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
    get_space_or_404(session, tenant_id, space_id)
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
    require_staff(current_user)
    get_space_or_404(session, tenant_id, space_id)
    spec = get_module_spec(module_key)
    if not spec or not spec.import_enabled:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该模块不支持导入")
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="仅支持 .xlsx 文件")
    try:
        content = read_upload_with_limit(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
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
