from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    department: Optional[str] = None
    # 平台门户角色：system_admin | security_fo | function_fo（与 JWT 无耦合，以库表为准）
    platform_role: str = Field(default="security_fo", max_length=32)
    is_active: bool = True
    is_superuser: bool = False
    is_approved: bool = True
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: Optional[str] = Field(default=None, unique=True, index=True)
    is_archived: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class TenantCreatorAllowlist(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="user.id")


class TenantMembership(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(default="tenant_member")
    created_at: datetime = Field(default_factory=utc_now)


class ProjectSpace(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "space_key", name="uq_space_tenant_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    space_key: str = Field(index=True)
    name: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class QuestionnaireQuestion(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "key", name="uq_question_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    key: str
    title: str
    question_type: str = "text"
    is_required: bool = False
    sort_order: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TaxonomyNode(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "code", name="uq_taxonomy_code"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="taxonomynode.id")
    code: str = Field(index=True)
    name: str
    sort_order: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RelevanceRule(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", name="uq_relevance_rule_space"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    expression: str = ""
    updated_at: datetime = Field(default_factory=utc_now)


class RelevanceAssessmentSubmission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    submitter_user_id: int = Field(foreign_key="user.id", index=True)
    conclusion: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class RelevanceAssessmentAnswer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    submission_id: int = Field(foreign_key="relevanceassessmentsubmission.id", index=True)
    question_key: str
    answer_value: str


class LifecycleFieldConfig(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "field_key", name="uq_lifecycle_field_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    field_key: str
    field_label: str
    field_type: str = "text"
    is_required: bool = False
    options_json: Optional[str] = None
    validation_json: Optional[str] = None
    sort_order: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FieldCatalogEntry(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "field_name", name="uq_field_catalog_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    field_name: str
    identifier_key: str
    data_type: str = "string"
    sensitivity_level: Optional[str] = None
    source_system: Optional[str] = None
    taxonomy_code: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FieldRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    requester_user_id: int = Field(foreign_key="user.id", index=True)
    field_name: str
    reason: Optional[str] = None
    status: str = "pending"
    review_comment: Optional[str] = None
    reviewed_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)
    reviewed_at: Optional[datetime] = None


class BusinessFunctionOption(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "option_name", name="uq_business_option_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    option_name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class BusinessFunctionOptionRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    requester_user_id: int = Field(foreign_key="user.id", index=True)
    option_name: str
    reason: Optional[str] = None
    status: str = "pending"
    review_comment: Optional[str] = None
    reviewed_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now)


class FieldUsageReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    submitter_user_id: int = Field(foreign_key="user.id", index=True)
    title: Optional[str] = None
    status: str = "pending_review"
    review_comment: Optional[str] = None
    reviewed_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)


class FieldUsageReportItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    report_id: int = Field(foreign_key="fieldusagereport.id", index=True)
    field_name: str
    value_text: str = ""


class ClassificationMatrix(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("tenant_id", "project_space_id", "name", name="uq_classification_matrix_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    name: str
    description: Optional[str] = None
    cells_json: str = "[]"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ClassificationRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    name: str
    priority: int = 100
    condition_json: str = "{}"
    output_sensitivity: str = "未分级"
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ClassificationResult(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_space_id", "field_catalog_entry_id", name="uq_classification_result_entry"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    field_catalog_entry_id: int = Field(foreign_key="fieldcatalogentry.id", index=True)
    sensitivity_level: str = "未分级"
    taxonomy_node_id: Optional[int] = Field(default=None, foreign_key="taxonomynode.id")
    matched_rule_id: Optional[int] = Field(default=None, foreign_key="classificationrule.id")
    applied_matrix: bool = False
    is_manual_override: bool = False
    manual_level: Optional[str] = None
    manual_reason: Optional[str] = None
    manual_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    manual_at: Optional[datetime] = None
    explanation_json: Optional[str] = None
    last_recompute_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=utc_now)


class ClassificationAuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    behavior_key: str
    label_snapshot: Optional[str] = None
    detail_json: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class FieldClassGrade(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_space_id", "field_catalog_entry_id", name="uq_field_class_grade_entry"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    field_catalog_entry_id: int = Field(foreign_key="fieldcatalogentry.id", index=True)
    grade_label: str
    notes: Optional[str] = None
    updated_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    updated_at: datetime = Field(default_factory=utc_now)


class FieldSecurityRequirement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    field_catalog_entry_id: int = Field(foreign_key="fieldcatalogentry.id", index=True)
    requirement_name: str
    check_kind: str
    check_json: str = "{}"
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class GovernanceChangeLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    project_space_id: int = Field(foreign_key="projectspace.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    behavior_key: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    summary: Optional[str] = None
    detail_json: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
