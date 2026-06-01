"""门户 FO 绑定、字段目录变更申请与审批动作。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.dsms_auth import is_staff, require_function_fo, require_staff
from app.api.dsms_helpers import get_space_or_404
from app.core.deps import require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import User
from app.models_portal import ApprovalRequest, BusinessFunction, FoUserFunctionBinding
from app.schemas_portal import (
    ApprovalRejectIn,
    FieldCatalogChangeApplyIn,
    FoBindingApplyIn,
    FoBindingSetIn,
    FoBindingsOut,
)
from app.services.approval_service import (
    APPROVAL_STATUS_PENDING,
    APPROVAL_TYPE_FO_FUNCTION_BINDING,
    _resolve_function_ids,
    apply_fo_bindings_for_user,
    approve_request,
    create_field_catalog_change_request,
    create_fo_binding_request,
    reject_request,
)

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-portal-approvals"])


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
    "/tenants/{tenant_id}/spaces/{space_id}/fo-function-bindings/me",
    description="权限：tenant_member。当前用户生效的业务功能绑定。",
)
def get_my_fo_bindings(
    tenant_id: int,
    space_id: int,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
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
    require_function_fo(current_user)
    get_space_or_404(session, tenant_id, space_id)
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
    require_function_fo(current_user)
    get_space_or_404(session, tenant_id, space_id)
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
    require_staff(current_user)
    get_space_or_404(session, tenant_id, space_id)
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
    require_staff(current_user)
    get_space_or_404(session, tenant_id, space_id)
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
    get_space_or_404(session, tenant_id, space_id)
    if not is_staff(current_user):
        return {"count": 0}
    rows = session.exec(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.project_space_id == space_id,
            ApprovalRequest.status == APPROVAL_STATUS_PENDING,
        )
    ).all()
    return {"count": len(rows)}
