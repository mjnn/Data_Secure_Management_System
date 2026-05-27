"""删除项目（tenant）及其全部关联数据。"""

from sqlmodel import Session, select

from app.models import (
    BusinessFunctionOption,
    BusinessFunctionOptionRequest,
    ClassificationAuditLog,
    ClassificationMatrix,
    ClassificationResult,
    ClassificationRule,
    FieldCatalogEntry,
    FieldClassGrade,
    FieldRequest,
    FieldSecurityRequirement,
    FieldUsageReport,
    FieldUsageReportItem,
    GovernanceChangeLog,
    LifecycleFieldConfig,
    ProjectSpace,
    QuestionnaireQuestion,
    RelevanceAssessmentAnswer,
    RelevanceAssessmentSubmission,
    RelevanceRule,
    TaxonomyNode,
    Tenant,
    TenantMembership,
)
from app.models_portal import (
    ApprovalRequest,
    BusinessFunction,
    DocumentResource,
    DocumentTransferJob,
    FieldCatalogChangeRequest,
    FieldCatalogValue,
    FoFunctionSecurityTag,
    FoUserFunctionBinding,
    PlatformAuditLog,
    SecurityRequirementRule,
    SensitivityLevel,
    SubmissionTask,
    SubmissionTaskAssignee,
    TaxonomyLevel,
)
from app.services.portal_seed import DEFAULT_TENANT_SLUG

_DELETE_ORDER = (
    RelevanceAssessmentAnswer,
    RelevanceAssessmentSubmission,
    SubmissionTaskAssignee,
    FoFunctionSecurityTag,
    FoUserFunctionBinding,
    ApprovalRequest,
    SubmissionTask,
    FieldCatalogValue,
    FieldClassGrade,
    FieldSecurityRequirement,
    ClassificationResult,
    ClassificationAuditLog,
    FieldCatalogChangeRequest,
    FieldUsageReportItem,
    FieldUsageReport,
    ClassificationRule,
    ClassificationMatrix,
    FieldRequest,
    BusinessFunctionOptionRequest,
    BusinessFunctionOption,
    FieldCatalogEntry,
    LifecycleFieldConfig,
    QuestionnaireQuestion,
    RelevanceRule,
    TaxonomyLevel,
    SensitivityLevel,
    SecurityRequirementRule,
    GovernanceChangeLog,
    DocumentTransferJob,
    DocumentResource,
    BusinessFunction,
    ProjectSpace,
    PlatformAuditLog,
    TenantMembership,
)


def _delete_taxonomy_nodes(session: Session, tenant_id: int) -> None:
    while True:
        nodes = session.exec(select(TaxonomyNode).where(TaxonomyNode.tenant_id == tenant_id)).all()
        if not nodes:
            return
        ids = {n.id for n in nodes}
        leaves = [n for n in nodes if n.parent_id is None or n.parent_id not in ids]
        if not leaves:
            leaves = [nodes[0]]
        for node in leaves:
            session.delete(node)
        session.flush()


def _delete_rows(session: Session, model, tenant_id: int) -> int:
    rows = session.exec(select(model).where(model.tenant_id == tenant_id)).all()
    for row in rows:
        session.delete(row)
    return len(rows)


def delete_tenant_cascade(session: Session, tenant_id: int) -> dict:
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        return {"ok": False, "reason": "not_found", "message": "项目不存在"}
    if tenant.slug == DEFAULT_TENANT_SLUG:
        return {"ok": False, "reason": "protected", "message": "默认项目不可删除"}

    counts: dict[str, int] = {}
    _delete_taxonomy_nodes(session, tenant_id)
    counts["taxonomy_nodes"] = 0

    for model in _DELETE_ORDER:
        name = model.__tablename__
        counts[name] = _delete_rows(session, model, tenant_id)

    session.delete(tenant)
    counts["tenant"] = 1
    return {"ok": True, "message": "项目已删除", "counts": counts}
