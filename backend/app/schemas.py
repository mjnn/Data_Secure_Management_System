from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Page(BaseModel):
    total: int
    items: list


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserMeOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    department: Optional[str]
    platform_role: str
    is_active: bool
    is_superuser: bool


class UserMeUpdateIn(BaseModel):
    email: Optional[str] = Field(default=None, min_length=1, max_length=200)
    full_name: Optional[str] = Field(default=None, max_length=200)
    department: Optional[str] = Field(default=None, max_length=200)


class UserPasswordChangeIn(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class TenantCreatorUpdate(BaseModel):
    user_ids: list[int]


class PlatformUsersBatchDeactivateIn(BaseModel):
    user_ids: list[int]


class PlatformUsersPlatformRoleIn(BaseModel):
    user_ids: list[int]
    platform_role: str


class TenantCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100)


class TenantPatchIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100)
    is_archived: Optional[bool] = None


class TenantOut(BaseModel):
    id: int
    name: str
    slug: Optional[str]
    is_archived: bool
    created_at: datetime


class MemberBatchIn(BaseModel):
    user_ids: list[int]
    role: str = "tenant_member"


class MemberBatchRemoveIn(BaseModel):
    user_ids: list[int]


class MemberRoleUpdateIn(BaseModel):
    role: str


class UserDirectoryOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    department: Optional[str]
    is_active: bool
    is_superuser: bool = False
    platform_role: str = "security_fo"
    created_at: datetime
    in_tenant: Optional[bool] = None
    tenant_role: Optional[str] = None


class UserImportItem(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    department: Optional[str]
    is_active: bool
    created_at: datetime
    temporary_password: Optional[str] = None


class SpaceCreateIn(BaseModel):
    space_key: str
    name: str


class SpaceUpdateIn(BaseModel):
    id: int
    name: str


class SpaceDeleteIn(BaseModel):
    ids: list[int]


class SpaceOut(BaseModel):
    id: int
    tenant_id: int
    space_key: str
    name: str
    created_at: datetime


class QuestionCreateIn(BaseModel):
    key: str
    title: str
    question_type: str = "single_select"
    is_required: bool = False
    sort_order: int = 0
    options_json: Optional[str] = None


class QuestionUpdateIn(BaseModel):
    id: int
    title: str
    question_type: str = "single_select"
    is_required: bool = False
    sort_order: int = 0
    options_json: Optional[str] = None


class QuestionDeleteIn(BaseModel):
    ids: list[int]


class QuestionOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    key: str
    title: str
    question_type: str
    is_required: bool
    sort_order: int
    options_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TaxonomyNodeCreateIn(BaseModel):
    code: str
    name: str
    parent_id: Optional[int] = None
    sort_order: int = 0


class TaxonomyNodeUpdateIn(BaseModel):
    code: str
    name: str
    parent_id: Optional[int] = None
    sort_order: int = 0


class TaxonomyNodeOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    parent_id: Optional[int]
    code: str
    name: str
    sort_order: int


class RelevanceRuleIn(BaseModel):
    expression: str = ""


class RelevanceRuleOut(BaseModel):
    tenant_id: int
    project_space_id: int
    expression: str


class SensitivityLevelOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    sort_order: int


class TaxonomyLevelCreateIn(BaseModel):
    level: int
    name: str
    description: Optional[str] = None
    sort_order: int = 0


class TaxonomyLevelUpdateIn(BaseModel):
    level: int
    name: str
    description: Optional[str] = None
    sort_order: int = 0


class TaxonomyLevelOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    level: int
    name: str
    description: Optional[str] = None
    sort_order: int
    updated_at: datetime


class RelevanceAssessmentAnswerIn(BaseModel):
    question_key: str
    answer_value: str


class RelevanceAssessmentCreateIn(BaseModel):
    conclusion: Optional[str] = None
    answers: list[RelevanceAssessmentAnswerIn]


class RelevanceAssessmentOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    submitter_user_id: int
    conclusion: Optional[str]
    created_at: datetime
    answers: list[RelevanceAssessmentAnswerIn]


class LifecycleFieldConfigCreateIn(BaseModel):
    field_key: str
    field_label: str
    field_type: str = "text"
    is_required: bool = False
    options_json: Optional[str] = None
    validation_json: Optional[str] = None
    sort_order: int = 0


class LifecycleFieldConfigUpdateIn(BaseModel):
    field_label: str
    field_type: str = "text"
    is_required: bool = False
    options_json: Optional[str] = None
    validation_json: Optional[str] = None
    sort_order: int = 0


class LifecycleFieldConfigOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    field_key: str
    field_label: str
    field_type: str
    is_builtin: bool = False
    is_required: bool
    options_json: Optional[str]
    validation_json: Optional[str]
    sort_order: int


class FieldCatalogCreateIn(BaseModel):
    field_name: str
    identifier_key: str
    data_type: str = "string"
    sensitivity_level: Optional[str] = None
    source_system: Optional[str] = None
    taxonomy_code: Optional[str] = None


class FieldCatalogUpdateIn(BaseModel):
    field_name: str
    identifier_key: str
    data_type: str = "string"
    sensitivity_level: Optional[str] = None
    source_system: Optional[str] = None
    taxonomy_code: Optional[str] = None


class FieldCatalogOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    field_name: str
    description: Optional[str] = None
    identifier_key: str
    data_type: str
    sensitivity_level: Optional[str]
    source_system: Optional[str]
    taxonomy_code: Optional[str] = None


class FieldRequestCreateIn(BaseModel):
    field_name: str
    reason: Optional[str] = None


class FieldRequestReviewIn(BaseModel):
    status: str
    review_comment: Optional[str] = None


class FieldRequestOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    requester_user_id: int
    field_name: str
    reason: Optional[str]
    status: str
    review_comment: Optional[str]


class BusinessFunctionOptionOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    option_name: str
    description: Optional[str]
    is_active: bool


class BusinessFunctionOptionRequestCreateIn(BaseModel):
    option_name: str
    reason: Optional[str] = None


class BusinessFunctionOptionRequestReviewIn(BaseModel):
    status: str
    review_comment: Optional[str] = None


class BusinessFunctionOptionRequestOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    requester_user_id: int
    option_name: str
    reason: Optional[str]
    status: str
    review_comment: Optional[str]


class FieldUsageReportItemIn(BaseModel):
    field_name: str
    value_text: str = ""


class FieldUsageReportCreateIn(BaseModel):
    title: Optional[str] = None
    items: list[FieldUsageReportItemIn]


class FieldUsageReportItemOut(BaseModel):
    id: int
    field_name: str
    value_text: str


class FieldUsageReportOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    submitter_user_id: int
    title: Optional[str]
    status: str
    review_comment: Optional[str]
    created_at: datetime
    items: list[FieldUsageReportItemOut] = []
    behavior_key: Optional[str] = None


class FieldUsageReportListItemOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    submitter_user_id: int
    title: Optional[str]
    status: str
    created_at: datetime
    item_count: int = 0


class FieldUsageReportReviewIn(BaseModel):
    status: str
    review_comment: Optional[str] = None


class IdentifierSuggestIn(BaseModel):
    seed: str = Field(min_length=1, max_length=200)


class IdentifierSuggestOut(BaseModel):
    suggested_key: str
    behavior_key: Optional[str] = None


# --- Phase 2: classification ---


class ClassificationMatrixCreateIn(BaseModel):
    name: str
    description: Optional[str] = None
    cells_json: str = "[]"


class ClassificationMatrixUpdateIn(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    cells_json: str = "[]"


class ClassificationMatrixOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    name: str
    description: Optional[str]
    cells_json: str
    created_at: datetime
    updated_at: datetime


class ClassificationMatrixBatchImportIn(BaseModel):
    items: list[ClassificationMatrixCreateIn]


class ClassificationRuleCreateIn(BaseModel):
    name: str
    priority: int = 100
    condition_json: str = "{}"
    output_sensitivity: str = "未分级"
    is_active: bool = True


class ClassificationRuleUpdateIn(BaseModel):
    id: int
    name: str
    priority: int = 100
    condition_json: str = "{}"
    output_sensitivity: str = "未分级"
    is_active: bool = True


class ClassificationRuleOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    name: str
    priority: int
    condition_json: str
    output_sensitivity: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClassificationResultOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    field_catalog_entry_id: int
    sensitivity_level: str
    taxonomy_node_id: Optional[int]
    matched_rule_id: Optional[int]
    applied_matrix: bool
    is_manual_override: bool
    manual_level: Optional[str]
    manual_reason: Optional[str]
    manual_by_user_id: Optional[int]
    manual_at: Optional[datetime]
    explanation_json: Optional[str]
    last_recompute_at: Optional[datetime]
    updated_at: datetime


class ClassificationManualIn(BaseModel):
    sensitivity_level: str
    reason: Optional[str] = None


class ClassificationAuditOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    user_id: int
    behavior_key: str
    label_snapshot: Optional[str]
    detail_json: Optional[str]
    created_at: datetime


class FieldClassGradeRowIn(BaseModel):
    field_catalog_entry_id: int
    grade_label: str
    notes: Optional[str] = None


class FieldClassGradePutIn(BaseModel):
    grades: list[FieldClassGradeRowIn]


class FieldClassGradeOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    field_catalog_entry_id: int
    grade_label: str
    notes: Optional[str]
    updated_by_user_id: Optional[int]
    updated_at: datetime


class FieldSecurityRequirementCreateIn(BaseModel):
    field_catalog_entry_id: int
    requirement_name: str
    check_kind: str
    check_json: str = "{}"
    is_active: bool = True


class FieldSecurityRequirementUpdateIn(BaseModel):
    requirement_name: str
    check_kind: str
    check_json: str = "{}"
    is_active: bool = True


class FieldSecurityRequirementOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    field_catalog_entry_id: int
    requirement_name: str
    check_kind: str
    check_json: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FieldSecurityEvalIn(BaseModel):
    field_catalog_entry_ids: Optional[list[int]] = None


class FieldSecurityEvalItemOut(BaseModel):
    field_catalog_entry_id: int
    field_name: str
    current_grade_label: Optional[str]
    passed: bool
    requirements: list[dict[str, Any]]


class FieldSecurityEvalOut(BaseModel):
    items: list[FieldSecurityEvalItemOut]
    behavior_key: Optional[str] = None


# --- Phase 3 ---


class GovernanceChangeLogOut(BaseModel):
    id: int
    tenant_id: int
    project_space_id: int
    user_id: int
    behavior_key: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    summary: Optional[str]
    detail_json: Optional[str]
    created_at: datetime


class ConfigImportIn(BaseModel):
    bundle: dict
    target_tenant_id: Optional[int] = None
    target_project_space_id: Optional[int] = None


class ConfigBatchDeleteIn(BaseModel):
    classification_matrix_ids: list[int] = []
    classification_rule_ids: list[int] = []
