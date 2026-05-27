from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlatformAuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    behavior_key: str
    label_snapshot: Optional[str] = None
    detail_json: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class BusinessFunction(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "function_key", name="uq_business_function_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    function_key: str
    name: str
    description: Optional[str] = None
    requires_fo_binding: bool = False
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FoUserFunctionBinding(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_space_id", "user_id", "business_function_id", name="uq_fo_function_binding"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    business_function_id: int = Field(foreign_key="businessfunction.id", index=True)
    status: str = Field(default="active", max_length=32)
    approved_via_request_id: Optional[int] = Field(default=None, foreign_key="approvalrequest.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FoFunctionSecurityTag(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_space_id", "business_function_id", "user_id", name="uq_fo_security_tag"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    business_function_id: int = Field(foreign_key="businessfunction.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    irrelevant: bool = False
    tagged_at: datetime = Field(default_factory=utc_now)
    submission_task_id: Optional[int] = Field(default=None, foreign_key="submissiontask.id")


class ApprovalRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    request_type: str = Field(max_length=64, index=True)
    status: str = Field(default="pending", max_length=32, index=True)
    title: str
    payload_json: str = "{}"
    requester_user_id: int = Field(foreign_key="user.id", index=True)
    reviewer_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    reject_reason: Optional[str] = None
    requested_at: datetime = Field(default_factory=utc_now)
    reviewed_at: Optional[datetime] = None


class SubmissionTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    business_function_id: int = Field(foreign_key="businessfunction.id", index=True)
    title: str
    internal_note: Optional[str] = None
    status: str = Field(default="draft", max_length=32)
    dispatch_note: Optional[str] = None
    dispatched_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    fo_fill_status: str = Field(default="not_started", max_length=32)
    fo_fill_content_summary: Optional[str] = None
    fo_fill_form_snapshot_json: Optional[str] = None
    fo_fill_lifecycle_rows_json: Optional[str] = None
    fo_cancellation_requested: bool = False
    fo_cancellation_reason: Optional[str] = None
    fo_cancel_approval_pending: bool = False
    fo_workflow_step: Optional[str] = Field(default=None, max_length=32)
    fo_relevance_conclusion: Optional[str] = Field(default=None, max_length=32)
    fo_relevance_fill_row_json: Optional[str] = None
    fo_governance_result_json: Optional[str] = None
    audit_status: Optional[str] = Field(default=None, max_length=32)
    audit_comment: Optional[str] = None
    audited_at: Optional[datetime] = None
    created_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    assignee_user_id: Optional[int] = Field(default=None, foreign_key="user.id")


class SubmissionTaskAssignee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    submission_task_id: int = Field(foreign_key="submissiontask.id", index=True)
    label: str
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    fo_fill_status: str = Field(default="not_started", max_length=32)
    fo_fill_content_summary: Optional[str] = None
    fo_fill_form_snapshot_json: Optional[str] = None
    fo_cancellation_requested: bool = False
    fo_cancellation_reason: Optional[str] = None


class FieldCatalogValue(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_space_id", "field_catalog_entry_id", "field_key", name="uq_catalog_value_key"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    field_catalog_entry_id: int = Field(foreign_key="fieldcatalogentry.id", index=True)
    field_key: str
    value_text: str = ""


class FieldCatalogChangeRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    request_type: str = Field(max_length=32)
    catalog_entry_id: Optional[int] = Field(default=None, foreign_key="fieldcatalogentry.id")
    proposed_label: str = ""
    proposed_description: Optional[str] = None
    status: str = Field(default="pending", max_length=32)
    requester_user_id: int = Field(foreign_key="user.id", index=True)
    reject_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class TaxonomyLevel(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "level", name="uq_taxonomy_level_num"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    level: int
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    updated_at: datetime = Field(default_factory=utc_now)


class SensitivityLevel(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "code", name="uq_sensitivity_code"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    code: str
    label: str
    description: Optional[str] = None
    sort_order: int = 0
    updated_at: datetime = Field(default_factory=utc_now)


class SecurityRequirementRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    rule_name: str
    trigger_root_json: str = "{}"
    action_content_html: str = ""
    is_active: bool = True
    updated_at: datetime = Field(default_factory=utc_now)


class DocumentResource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: Optional[int] = Field(default=None, foreign_key="projectspace.id", index=True)
    resource_kind: str = Field(max_length=32, index=True)
    module_key: Optional[str] = Field(default=None, max_length=64, index=True)
    title: str
    description: Optional[str] = None
    original_file_name: str
    mime_type: str = "application/octet-stream"
    file_size_bytes: int = 0
    storage_path: str
    checksum_sha256: Optional[str] = None
    tags_json: Optional[str] = None
    regulation_meta_json: Optional[str] = None
    uploaded_by_user_id: int = Field(foreign_key="user.id", index=True)
    is_archived: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DocumentTransferJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    direction: str = Field(max_length=16)
    module_key: str = Field(max_length=64)
    status: str = Field(default="pending", max_length=32, index=True)
    source_resource_id: Optional[int] = Field(default=None, foreign_key="documentresource.id")
    result_resource_id: Optional[int] = Field(default=None, foreign_key="documentresource.id")
    request_params_json: Optional[str] = None
    result_summary_json: Optional[str] = None
    error_message: Optional[str] = None
    created_by_user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
