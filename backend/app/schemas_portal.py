from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, Field


class DocumentModuleOut(BaseModel):
    module_key: str
    title: str
    import_enabled: bool
    export_enabled: bool
    template_filename: str


class DocumentResourceOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: Optional[int]
    resource_kind: str
    module_key: Optional[str]
    title: str
    description: Optional[str]
    original_file_name: str
    mime_type: str
    file_size_bytes: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class DocumentResourcePatchIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None
    tags_json: Optional[str] = None
    regulation_meta_json: Optional[str] = None


class DocumentTransferJobOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    direction: str
    module_key: str
    status: str
    source_resource_id: Optional[int]
    result_resource_id: Optional[int]
    result_summary_json: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class DocumentExportIn(BaseModel):
    module_key: str = Field(min_length=1, max_length=64)


class ApprovalRequestOut(BaseModel):
    id: int
    request_type: str
    status: str
    title: str
    payload_json: str
    requester_user_id: int
    reviewer_user_id: Optional[int]
    reject_reason: Optional[str]
    requested_at: datetime
    reviewed_at: Optional[datetime]


class SubmissionTaskOut(BaseModel):
    id: int
    business_function_id: int
    function_key: Optional[str] = None
    function_name: Optional[str] = None
    title: str
    internal_note: Optional[str] = None
    status: str
    dispatch_note: Optional[str] = None
    dispatched_at: Optional[datetime] = None
    created_at: datetime
    fo_fill_status: str
    fo_fill_content_summary: Optional[str] = None
    fo_cancellation_requested: bool = False
    fo_cancel_approval_pending: bool = False
    fo_workflow_step: Optional[str] = None
    fo_relevance_conclusion: Optional[str] = None
    audit_status: Optional[str] = None
    audit_comment: Optional[str] = None
    audited_at: Optional[datetime] = None
    assignee_user_id: Optional[int] = None
    # 前端兼容字段（GET 详情时填充）
    functionId: Optional[str] = None
    internalNote: Optional[str] = None
    dispatchNote: Optional[str] = None
    foFillStatus: Optional[str] = None


class SubmissionTaskCreateIn(BaseModel):
    function_key: str
    title: str = Field(min_length=1, max_length=200)
    internal_note: Optional[str] = None


class SubmissionTaskPatchIn(BaseModel):
    fields: dict


class SubmissionTaskDispatchIn(BaseModel):
    task_ids: list[int]
    dispatch_note: str = Field(min_length=1)


class SubmissionTasksCopyApprovedIn(BaseModel):
    source_tenant_id: int
    source_project_space_id: int


class FoBindingApplyIn(BaseModel):
    desired_function_keys: list[str]
    reason: Optional[str] = ""


class FoBindingsOut(BaseModel):
    function_keys: list[str] = []
    has_pending_binding_request: bool = False


class FoBindingSetIn(BaseModel):
    function_keys: list[str] = []


class FieldCatalogChangeApplyIn(BaseModel):
    request_type: str
    proposed_label: str
    proposed_description: Optional[str] = ""
    catalog_entry_id: Optional[int] = None


class ApprovalRejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ApprovalRequestDetailOut(BaseModel):
    id: int
    request_type: str
    type: str
    status: str
    title: str
    payload: dict
    requester_user_id: int
    reviewer_user_id: Optional[int] = None
    requestedBy: str = ""
    reviewedBy: str = ""
    rejectReason: str = ""
    requestedAt: str = ""
    reviewedAt: str = ""


class BusinessFunctionOut(BaseModel):
    id: int
    function_key: str
    name: str
    description: Optional[str]
    requires_fo_binding: bool
    has_active_fo_binding: bool = False
    sort_order: int
    is_active: bool
