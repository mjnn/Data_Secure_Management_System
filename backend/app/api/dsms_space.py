import csv
import re
from datetime import datetime, timezone
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from sqlmodel import Session, col, delete, func, or_, select

from app.api.dsms_helpers import (
    generate_temporary_password,
    get_space_or_404,
    page_limit,
    suggest_identifier_key_from_seed,
)
from app.core.config import settings
from app.core.deps import (
    get_current_user,
    get_membership,
    require_super_admin,
    require_tenant_admin,
    require_tenant_member,
)
from app.core.database import get_session
from app.core.security import get_password_hash
from app.core.upload_utils import read_upload_with_limit
from app.models import (
    BusinessFunctionOption,
    BusinessFunctionOptionRequest,
    FieldCatalogEntry,
    FieldRequest,
    FieldUsageReport,
    FieldUsageReportItem,
    LifecycleFieldConfig,
    ProjectSpace,
    QuestionnaireQuestion,
    RelevanceAssessmentAnswer,
    RelevanceAssessmentSubmission,
    RelevanceRule,
    SensitivityLevel,
    TaxonomyLevel,
    TaxonomyNode,
    User,
)
from app.schemas import (
    BusinessFunctionOptionOut,
    BusinessFunctionOptionRequestCreateIn,
    BusinessFunctionOptionRequestOut,
    BusinessFunctionOptionRequestReviewIn,
    FieldCatalogCreateIn,
    FieldCatalogOut,
    FieldCatalogUpdateIn,
    FieldUsageReportCreateIn,
    FieldUsageReportItemOut,
    FieldUsageReportListItemOut,
    FieldUsageReportOut,
    FieldUsageReportReviewIn,
    FieldRequestCreateIn,
    FieldRequestOut,
    FieldRequestReviewIn,
    IdentifierSuggestIn,
    IdentifierSuggestOut,
    LifecycleFieldConfigCreateIn,
    LifecycleFieldConfigOut,
    LifecycleFieldConfigUpdateIn,
    Page,
    QuestionCreateIn,
    QuestionDeleteIn,
    QuestionOut,
    QuestionUpdateIn,
    RelevanceAssessmentCreateIn,
    RelevanceAssessmentOut,
    RelevanceAssessmentAnswerIn,
    RelevanceRuleIn,
    RelevanceRuleOut,
    SensitivityLevelOut,
    TaxonomyLevelCreateIn,
    TaxonomyLevelOut,
    TaxonomyLevelUpdateIn,
    TaxonomyNodeCreateIn,
    TaxonomyNodeOut,
    TaxonomyNodeUpdateIn,
)

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-space"])

@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/questionnaires/questions",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。问卷题目分页列表。",
)
def list_questions(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(QuestionnaireQuestion).where(
        QuestionnaireQuestion.tenant_id == tenant_id, QuestionnaireQuestion.project_space_id == space_id
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(stmt.order_by(QuestionnaireQuestion.sort_order).offset(skip).limit(limit)).all()
    return {"total": total, "items": [QuestionOut.model_validate(i, from_attributes=True).model_dump() for i in items]}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/questionnaires/questions",
    response_model=QuestionOut,
    description="权限：tenant_admin（同项目）或 super_admin。创建问卷题目。",
)
def create_question(
    tenant_id: int,
    space_id: int,
    payload: QuestionCreateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    item = QuestionnaireQuestion(tenant_id=tenant_id, project_space_id=space_id, **payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return QuestionOut.model_validate(item, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/questionnaires/questions",
    response_model=QuestionOut,
    description="权限：tenant_admin（同项目）或 super_admin。更新问卷题目。",
)
def update_question(
    tenant_id: int,
    space_id: int,
    payload: QuestionUpdateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    item = session.get(QuestionnaireQuestion, payload.id)
    if not item or item.tenant_id != tenant_id or item.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    item.title = payload.title
    item.question_type = payload.question_type
    item.is_required = payload.is_required
    item.sort_order = payload.sort_order
    if payload.options_json is not None:
        item.options_json = payload.options_json
    item.updated_at = datetime.now(timezone.utc)
    session.add(item)
    session.commit()
    session.refresh(item)
    return QuestionOut.model_validate(item, from_attributes=True)


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/questionnaires/questions/delete",
    description="权限：tenant_admin（同项目）或 super_admin。批量删除问卷题目。",
)
def delete_questions(
    tenant_id: int,
    space_id: int,
    payload: QuestionDeleteIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    for qid in payload.ids:
        item = session.get(QuestionnaireQuestion, qid)
        if item and item.tenant_id == tenant_id and item.project_space_id == space_id:
            session.delete(item)
    session.commit()
    return {"deleted_ids": payload.ids, "behavior_key": "questionnaire/questions/delete"}


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/taxonomy/nodes",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。分类节点分页列表。",
)
def list_taxonomy_nodes(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(TaxonomyNode).where(TaxonomyNode.tenant_id == tenant_id, TaxonomyNode.project_space_id == space_id)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(stmt.order_by(TaxonomyNode.sort_order, TaxonomyNode.id).offset(skip).limit(limit)).all()
    return {"total": total, "items": [TaxonomyNodeOut.model_validate(i, from_attributes=True).model_dump() for i in items]}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/taxonomy/nodes",
    response_model=TaxonomyNodeOut,
    description="权限：tenant_admin（同项目）或 super_admin。创建分类节点。",
)
def create_taxonomy_node(
    tenant_id: int,
    space_id: int,
    payload: TaxonomyNodeCreateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    node = TaxonomyNode(tenant_id=tenant_id, project_space_id=space_id, **payload.model_dump())
    session.add(node)
    session.commit()
    session.refresh(node)
    return TaxonomyNodeOut.model_validate(node, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/taxonomy/nodes/{node_id}",
    response_model=TaxonomyNodeOut,
    description="权限：tenant_admin（同项目）或 super_admin。更新分类节点。",
)
def update_taxonomy_node(
    tenant_id: int,
    space_id: int,
    node_id: int,
    payload: TaxonomyNodeUpdateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    node = session.get(TaxonomyNode, node_id)
    if not node or node.tenant_id != tenant_id or node.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类节点不存在")
    for k, v in payload.model_dump().items():
        setattr(node, k, v)
    node.updated_at = datetime.now(timezone.utc)
    session.add(node)
    session.commit()
    session.refresh(node)
    return TaxonomyNodeOut.model_validate(node, from_attributes=True)


@router.delete(
    "/tenants/{tenant_id}/spaces/{space_id}/taxonomy/nodes/{node_id}",
    description="权限：tenant_admin（同项目）或 super_admin。删除分类节点。",
)
def delete_taxonomy_node(
    tenant_id: int,
    space_id: int,
    node_id: int,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    node = session.get(TaxonomyNode, node_id)
    if not node or node.tenant_id != tenant_id or node.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类节点不存在")
    session.delete(node)
    session.commit()
    return {"deleted_id": node_id, "behavior_key": "taxonomy-nodes/delete"}


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/relevance/rules",
    response_model=RelevanceRuleOut,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。读取相关性规则。",
)
def get_relevance_rule(
    tenant_id: int,
    space_id: int,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    rule = session.exec(
        select(RelevanceRule).where(RelevanceRule.tenant_id == tenant_id, RelevanceRule.project_space_id == space_id)
    ).first()
    if not rule:
        return RelevanceRuleOut(tenant_id=tenant_id, project_space_id=space_id, expression="")
    return RelevanceRuleOut.model_validate(rule, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/relevance/rules",
    response_model=RelevanceRuleOut,
    description="权限：tenant_admin（同项目）或 super_admin。更新相关性规则。",
)
def put_relevance_rule(
    tenant_id: int,
    space_id: int,
    payload: RelevanceRuleIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    rule = session.exec(
        select(RelevanceRule).where(RelevanceRule.tenant_id == tenant_id, RelevanceRule.project_space_id == space_id)
    ).first()
    if not rule:
        rule = RelevanceRule(tenant_id=tenant_id, project_space_id=space_id, expression=payload.expression)
    else:
        rule.expression = payload.expression
        rule.updated_at = datetime.now(timezone.utc)
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return RelevanceRuleOut.model_validate(rule, from_attributes=True)


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/relevance/assessments",
    response_model=RelevanceAssessmentOut,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。提交相关性判定填报。",
)
def create_relevance_assessment(
    tenant_id: int,
    space_id: int,
    payload: RelevanceAssessmentCreateIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    submission = RelevanceAssessmentSubmission(
        tenant_id=tenant_id,
        project_space_id=space_id,
        submitter_user_id=current_user.id,
        conclusion=payload.conclusion,
    )
    session.add(submission)
    session.flush()
    for answer in payload.answers:
        session.add(
            RelevanceAssessmentAnswer(
                tenant_id=tenant_id,
                submission_id=submission.id,
                question_key=answer.question_key,
                answer_value=answer.answer_value,
            )
        )
    session.commit()
    session.refresh(submission)
    return RelevanceAssessmentOut(
        id=submission.id,
        tenant_id=submission.tenant_id,
        project_space_id=submission.project_space_id,
        submitter_user_id=submission.submitter_user_id,
        conclusion=submission.conclusion,
        created_at=submission.created_at,
        answers=payload.answers,
    )


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/relevance/assessments/{submission_id}",
    response_model=RelevanceAssessmentOut,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。查看单条相关性判定填报。",
)
def get_relevance_assessment(
    tenant_id: int,
    space_id: int,
    submission_id: int,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    submission = session.get(RelevanceAssessmentSubmission, submission_id)
    if not submission or submission.tenant_id != tenant_id or submission.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="相关性填报不存在")
    answers = session.exec(
        select(RelevanceAssessmentAnswer).where(
            RelevanceAssessmentAnswer.tenant_id == tenant_id,
            RelevanceAssessmentAnswer.submission_id == submission_id,
        )
    ).all()
    return RelevanceAssessmentOut(
        id=submission.id,
        tenant_id=submission.tenant_id,
        project_space_id=submission.project_space_id,
        submitter_user_id=submission.submitter_user_id,
        conclusion=submission.conclusion,
        created_at=submission.created_at,
        answers=[RelevanceAssessmentAnswerIn(question_key=a.question_key, answer_value=a.answer_value) for a in answers],
    )


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/forms/lifecycle-field-config",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。分页查询填报字段配置。",
)
def list_lifecycle_field_config(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(LifecycleFieldConfig).where(
        LifecycleFieldConfig.tenant_id == tenant_id, LifecycleFieldConfig.project_space_id == space_id
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(stmt.order_by(LifecycleFieldConfig.sort_order, LifecycleFieldConfig.id).offset(skip).limit(limit)).all()
    return {"total": total, "items": [LifecycleFieldConfigOut.model_validate(i, from_attributes=True).model_dump() for i in items]}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/forms/lifecycle-field-config",
    response_model=LifecycleFieldConfigOut,
    description="权限：tenant_admin（同项目）或 super_admin。新增填报字段配置。",
)
def create_lifecycle_field_config(
    tenant_id: int,
    space_id: int,
    payload: LifecycleFieldConfigCreateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    item = LifecycleFieldConfig(tenant_id=tenant_id, project_space_id=space_id, **payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return LifecycleFieldConfigOut.model_validate(item, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/forms/lifecycle-field-config",
    response_model=LifecycleFieldConfigOut,
    description="权限：tenant_admin（同项目）或 super_admin。更新填报字段配置。",
)
def update_lifecycle_field_config(
    tenant_id: int,
    space_id: int,
    id: int,
    payload: LifecycleFieldConfigUpdateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    item = session.get(LifecycleFieldConfig, id)
    if not item or item.tenant_id != tenant_id or item.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字段配置不存在")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    item.updated_at = datetime.now(timezone.utc)
    session.add(item)
    session.commit()
    session.refresh(item)
    return LifecycleFieldConfigOut.model_validate(item, from_attributes=True)


@router.delete(
    "/tenants/{tenant_id}/spaces/{space_id}/forms/lifecycle-field-config",
    description="权限：tenant_admin（同项目）或 super_admin。删除填报字段配置。",
)
def delete_lifecycle_field_config(
    tenant_id: int,
    space_id: int,
    id: int,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    item = session.get(LifecycleFieldConfig, id)
    if not item or item.tenant_id != tenant_id or item.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字段配置不存在")
    session.delete(item)
    session.commit()
    return {"deleted_id": id, "behavior_key": "lifecycle-field-config"}


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/sensitivity-levels",
    response_model=Page,
    description="权限：tenant_member。密级定义列表。",
)
def list_sensitivity_levels(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(SensitivityLevel).where(
        SensitivityLevel.tenant_id == tenant_id,
        SensitivityLevel.project_space_id == space_id,
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(stmt.order_by(SensitivityLevel.sort_order, SensitivityLevel.id).offset(skip).limit(limit)).all()
    return {
        "total": total,
        "items": [SensitivityLevelOut.model_validate(i, from_attributes=True).model_dump() for i in items],
    }


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/taxonomy-levels",
    response_model=Page,
    description="权限：tenant_member。分类树层级列表。",
)
def list_taxonomy_levels(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(TaxonomyLevel).where(
        TaxonomyLevel.tenant_id == tenant_id,
        TaxonomyLevel.project_space_id == space_id,
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(
        stmt.order_by(TaxonomyLevel.sort_order, TaxonomyLevel.level).offset(skip).limit(limit)
    ).all()
    return {
        "total": total,
        "items": [TaxonomyLevelOut.model_validate(i, from_attributes=True).model_dump() for i in items],
    }


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/taxonomy-levels",
    response_model=TaxonomyLevelOut,
    description="权限：tenant_admin+。创建分类树层级。",
)
def create_taxonomy_level(
    tenant_id: int,
    space_id: int,
    payload: TaxonomyLevelCreateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    dup = session.exec(
        select(TaxonomyLevel).where(
            TaxonomyLevel.tenant_id == tenant_id,
            TaxonomyLevel.project_space_id == space_id,
            TaxonomyLevel.level == payload.level,
        )
    ).first()
    if dup:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"分类级 {payload.level} 已存在")
    row = TaxonomyLevel(
        tenant_id=tenant_id,
        project_space_id=space_id,
        level=payload.level,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return TaxonomyLevelOut.model_validate(row, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/taxonomy-levels/{level_id}",
    response_model=TaxonomyLevelOut,
    description="权限：tenant_admin+。更新分类树层级。",
)
def update_taxonomy_level(
    tenant_id: int,
    space_id: int,
    level_id: int,
    payload: TaxonomyLevelUpdateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    row = session.get(TaxonomyLevel, level_id)
    if not row or row.tenant_id != tenant_id or row.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类树层级不存在")
    dup = session.exec(
        select(TaxonomyLevel).where(
            TaxonomyLevel.tenant_id == tenant_id,
            TaxonomyLevel.project_space_id == space_id,
            TaxonomyLevel.level == payload.level,
            TaxonomyLevel.id != level_id,
        )
    ).first()
    if dup:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"分类级 {payload.level} 已被占用")
    row.level = payload.level
    row.name = payload.name
    row.description = payload.description
    row.sort_order = payload.sort_order
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return TaxonomyLevelOut.model_validate(row, from_attributes=True)


@router.delete(
    "/tenants/{tenant_id}/spaces/{space_id}/taxonomy-levels/{level_id}",
    description="权限：tenant_admin+。删除分类树层级。",
)
def delete_taxonomy_level(
    tenant_id: int,
    space_id: int,
    level_id: int,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    row = session.get(TaxonomyLevel, level_id)
    if not row or row.tenant_id != tenant_id or row.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类树层级不存在")
    session.delete(row)
    session.commit()
    return {"deleted_id": level_id, "behavior_key": "taxonomy-levels/delete"}


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/field-catalog",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。字段主表分页列表。",
)
def list_field_catalog(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(FieldCatalogEntry).where(
        FieldCatalogEntry.tenant_id == tenant_id, FieldCatalogEntry.project_space_id == space_id
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(stmt.order_by(FieldCatalogEntry.id).offset(skip).limit(limit)).all()
    return {"total": total, "items": [FieldCatalogOut.model_validate(i, from_attributes=True).model_dump() for i in items]}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/field-catalog",
    response_model=FieldCatalogOut,
    description="权限：tenant_admin（同项目）或 super_admin。新增字段主表条目。",
)
def create_field_catalog(
    tenant_id: int,
    space_id: int,
    payload: FieldCatalogCreateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    item = FieldCatalogEntry(tenant_id=tenant_id, project_space_id=space_id, **payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return FieldCatalogOut.model_validate(item, from_attributes=True)


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/field-catalog/{entry_id}",
    response_model=FieldCatalogOut,
    description="权限：tenant_admin（同项目）或 super_admin。更新字段主表条目。",
)
def update_field_catalog(
    tenant_id: int,
    space_id: int,
    entry_id: int,
    payload: FieldCatalogUpdateIn,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    item = session.get(FieldCatalogEntry, entry_id)
    if not item or item.tenant_id != tenant_id or item.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字段条目不存在")
    for k, v in payload.model_dump().items():
        setattr(item, k, v)
    item.updated_at = datetime.now(timezone.utc)
    session.add(item)
    session.commit()
    session.refresh(item)
    return FieldCatalogOut.model_validate(item, from_attributes=True)


@router.delete(
    "/tenants/{tenant_id}/spaces/{space_id}/field-catalog/{entry_id}",
    description="权限：tenant_admin（同项目）或 super_admin。删除字段主表条目。",
)
def delete_field_catalog(
    tenant_id: int,
    space_id: int,
    entry_id: int,
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    item = session.get(FieldCatalogEntry, entry_id)
    if not item or item.tenant_id != tenant_id or item.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字段条目不存在")
    session.delete(item)
    session.commit()
    return {"deleted_id": entry_id, "behavior_key": "field-catalog"}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/field-catalog/batch-import",
    description="权限：tenant_admin（同项目）或 super_admin。批量导入字段主表，重复项跳过。",
)
def batch_import_field_catalog(
    tenant_id: int,
    space_id: int,
    items: list[FieldCatalogCreateIn],
    _: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    created, skipped = 0, 0
    for row in items:
        exists = session.exec(
            select(FieldCatalogEntry).where(
                FieldCatalogEntry.tenant_id == tenant_id,
                FieldCatalogEntry.project_space_id == space_id,
                FieldCatalogEntry.field_name == row.field_name,
            )
        ).first()
        if exists:
            skipped += 1
            continue
        session.add(FieldCatalogEntry(tenant_id=tenant_id, project_space_id=space_id, **row.model_dump()))
        created += 1
    session.commit()
    return {"created_count": created, "skipped_count": skipped, "behavior_key": "field-catalog"}


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/field-catalog/value-options",
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。返回字段主表可选值快照。",
)
def field_catalog_value_options(
    tenant_id: int,
    space_id: int,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    items = session.exec(
        select(FieldCatalogEntry).where(
            FieldCatalogEntry.tenant_id == tenant_id, FieldCatalogEntry.project_space_id == space_id
        )
    ).all()
    return {
        "items": [{"id": i.id, "field_name": i.field_name, "identifier_key": i.identifier_key} for i in items],
        "behavior_key": "field-catalog",
    }


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/field-requests",
    response_model=FieldRequestOut,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。创建字段新增申请。",
)
def create_field_request(
    tenant_id: int,
    space_id: int,
    payload: FieldRequestCreateIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    item = FieldRequest(
        tenant_id=tenant_id,
        project_space_id=space_id,
        requester_user_id=current_user.id,
        field_name=payload.field_name,
        reason=payload.reason,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return FieldRequestOut.model_validate(item, from_attributes=True)


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/field-requests",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。字段申请分页列表。",
)
def list_field_requests(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(FieldRequest).where(FieldRequest.tenant_id == tenant_id, FieldRequest.project_space_id == space_id)
    if status_filter:
        stmt = stmt.where(FieldRequest.status == status_filter)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(stmt.order_by(FieldRequest.id.desc()).offset(skip).limit(limit)).all()
    return {"total": total, "items": [FieldRequestOut.model_validate(i, from_attributes=True).model_dump() for i in items]}


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/field-requests/{request_id}/review",
    response_model=FieldRequestOut,
    description="权限：tenant_admin（同项目）或 super_admin。审核字段新增申请。",
)
def review_field_request(
    tenant_id: int,
    space_id: int,
    request_id: int,
    payload: FieldRequestReviewIn,
    reviewer: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="审核状态仅支持 approved/rejected")
    item = session.get(FieldRequest, request_id)
    if not item or item.tenant_id != tenant_id or item.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字段申请不存在")
    item.status = payload.status
    item.review_comment = payload.review_comment
    item.reviewed_by_user_id = reviewer.id
    item.reviewed_at = datetime.now(timezone.utc)
    session.add(item)
    if payload.status == "approved":
        exists = session.exec(
            select(FieldCatalogEntry).where(
                FieldCatalogEntry.tenant_id == tenant_id,
                FieldCatalogEntry.project_space_id == space_id,
                FieldCatalogEntry.field_name == item.field_name,
            )
        ).first()
        if not exists:
            session.add(
                FieldCatalogEntry(
                    tenant_id=tenant_id,
                    project_space_id=space_id,
                    field_name=item.field_name,
                    identifier_key=item.field_name.lower().replace(" ", "_"),
                    data_type="string",
                )
            )
    session.commit()
    session.refresh(item)
    return FieldRequestOut.model_validate(item, from_attributes=True)


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/business-functions/options",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。业务功能选项列表。",
)
def list_business_function_options(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(BusinessFunctionOption).where(
        BusinessFunctionOption.tenant_id == tenant_id, BusinessFunctionOption.project_space_id == space_id
    )
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(stmt.order_by(BusinessFunctionOption.id.desc()).offset(skip).limit(limit)).all()
    return {"total": total, "items": [BusinessFunctionOptionOut.model_validate(i, from_attributes=True).model_dump() for i in items]}


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/business-functions/option-requests",
    response_model=BusinessFunctionOptionRequestOut,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。提交业务功能选项申请。",
)
def create_business_option_request(
    tenant_id: int,
    space_id: int,
    payload: BusinessFunctionOptionRequestCreateIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    item = BusinessFunctionOptionRequest(
        tenant_id=tenant_id,
        project_space_id=space_id,
        requester_user_id=current_user.id,
        option_name=payload.option_name,
        reason=payload.reason,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return BusinessFunctionOptionRequestOut.model_validate(item, from_attributes=True)


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/business-functions/option-requests",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。业务功能选项申请列表。",
)
def list_business_option_requests(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    stmt = select(BusinessFunctionOptionRequest).where(
        BusinessFunctionOptionRequest.tenant_id == tenant_id,
        BusinessFunctionOptionRequest.project_space_id == space_id,
    )
    if status_filter:
        stmt = stmt.where(BusinessFunctionOptionRequest.status == status_filter)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    items = session.exec(stmt.order_by(BusinessFunctionOptionRequest.id.desc()).offset(skip).limit(limit)).all()
    return {
        "total": total,
        "items": [BusinessFunctionOptionRequestOut.model_validate(i, from_attributes=True).model_dump() for i in items],
    }


@router.put(
    "/tenants/{tenant_id}/spaces/{space_id}/business-functions/option-requests/{request_id}/review",
    response_model=BusinessFunctionOptionRequestOut,
    description="权限：tenant_admin（同项目）或 super_admin。审核业务功能选项申请。",
)
def review_business_option_request(
    tenant_id: int,
    space_id: int,
    request_id: int,
    payload: BusinessFunctionOptionRequestReviewIn,
    reviewer: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="审核状态仅支持 approved/rejected")
    item = session.get(BusinessFunctionOptionRequest, request_id)
    if not item or item.tenant_id != tenant_id or item.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="业务功能选项申请不存在")
    item.status = payload.status
    item.review_comment = payload.review_comment
    item.reviewed_by_user_id = reviewer.id
    session.add(item)
    if payload.status == "approved":
        existing = session.exec(
            select(BusinessFunctionOption).where(
                BusinessFunctionOption.tenant_id == tenant_id,
                BusinessFunctionOption.project_space_id == space_id,
                BusinessFunctionOption.option_name == item.option_name,
            )
        ).first()
        if not existing:
            session.add(
                BusinessFunctionOption(
                    tenant_id=tenant_id,
                    project_space_id=space_id,
                    option_name=item.option_name,
                    description=item.reason,
                    is_active=True,
                )
            )
    session.commit()
    session.refresh(item)
    return BusinessFunctionOptionRequestOut.model_validate(item, from_attributes=True)


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/identifiers/suggest",
    response_model=IdentifierSuggestOut,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。根据种子文本建议 identifier_key。",
)
def suggest_identifier_key(
    tenant_id: int,
    space_id: int,
    payload: IdentifierSuggestIn,
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    key = suggest_identifier_key_from_seed(payload.seed)
    return IdentifierSuggestOut(suggested_key=key, behavior_key="suggest-identifier-key")


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/field-usage-reports",
    response_model=FieldUsageReportOut,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。提交字段填报单。",
)
def create_field_usage_report(
    tenant_id: int,
    space_id: int,
    payload: FieldUsageReportCreateIn,
    current_user: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="填报项不能为空")
    report = FieldUsageReport(
        tenant_id=tenant_id,
        project_space_id=space_id,
        submitter_user_id=current_user.id,
        title=payload.title,
        status="pending_review",
    )
    session.add(report)
    session.flush()
    for row in payload.items:
        session.add(
            FieldUsageReportItem(
                tenant_id=tenant_id,
                report_id=report.id,
                field_name=row.field_name,
                value_text=row.value_text or "",
            )
        )
    session.commit()
    session.refresh(report)
    items = session.exec(
        select(FieldUsageReportItem).where(
            FieldUsageReportItem.tenant_id == tenant_id,
            FieldUsageReportItem.report_id == report.id,
        )
    ).all()
    return FieldUsageReportOut(
        id=report.id,
        tenant_id=report.tenant_id,
        project_space_id=report.project_space_id,
        submitter_user_id=report.submitter_user_id,
        title=report.title,
        status=report.status,
        review_comment=report.review_comment,
        created_at=report.created_at,
        items=[FieldUsageReportItemOut.model_validate(i, from_attributes=True) for i in items],
        behavior_key="field-usage-reports",
    )


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/field-usage-reports",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。字段填报单分页列表。",
)
def list_field_usage_reports(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    get_space_or_404(session, tenant_id, space_id)
    stmt = select(FieldUsageReport).where(
        FieldUsageReport.tenant_id == tenant_id,
        FieldUsageReport.project_space_id == space_id,
    )
    if status_filter:
        stmt = stmt.where(FieldUsageReport.status == status_filter)
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    reports = session.exec(stmt.order_by(FieldUsageReport.id.desc()).offset(skip).limit(limit)).all()
    ids = [r.id for r in reports]
    counts: dict[int, int] = {}
    if ids:
        for it in session.exec(select(FieldUsageReportItem).where(FieldUsageReportItem.report_id.in_(ids))).all():
            counts[it.report_id] = counts.get(it.report_id, 0) + 1
    items_out = [
        FieldUsageReportListItemOut(
            id=r.id,
            tenant_id=r.tenant_id,
            project_space_id=r.project_space_id,
            submitter_user_id=r.submitter_user_id,
            title=r.title,
            status=r.status,
            created_at=r.created_at,
            item_count=counts.get(r.id, 0),
        ).model_dump()
        for r in reports
    ]
    return {"total": total, "items": items_out}


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/field-usage-reports/export",
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。导出字段填报明细为 CSV。",
)
def export_field_usage_reports(
    tenant_id: int,
    space_id: int,
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    get_space_or_404(session, tenant_id, space_id)
    r_stmt = select(FieldUsageReport).where(
        FieldUsageReport.tenant_id == tenant_id,
        FieldUsageReport.project_space_id == space_id,
    )
    if status_filter:
        r_stmt = r_stmt.where(FieldUsageReport.status == status_filter)
    reports = session.exec(r_stmt.order_by(FieldUsageReport.id.desc())).all()
    report_ids = [r.id for r in reports]
    items_by_report: dict[int, list[FieldUsageReportItem]] = {rid: [] for rid in report_ids}
    if report_ids:
        for it in session.exec(select(FieldUsageReportItem).where(FieldUsageReportItem.report_id.in_(report_ids))).all():
            items_by_report.setdefault(it.report_id, []).append(it)
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["report_id", "title", "report_status", "field_name", "value_text", "created_at"])
    for r in reports:
        its = items_by_report.get(r.id, [])
        if not its:
            w.writerow([r.id, r.title or "", r.status, "", "", r.created_at.isoformat()])
        else:
            for it in its:
                w.writerow([r.id, r.title or "", r.status, it.field_name, it.value_text, r.created_at.isoformat()])
    data = "\ufeff" + buf.getvalue()
    return StreamingResponse(
        iter([data.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="field-usage-reports.csv"'},
    )


@router.post(
    "/tenants/{tenant_id}/spaces/{space_id}/field-usage-reports/{report_id}/review",
    response_model=FieldUsageReportOut,
    description="权限：tenant_admin（同项目）或 super_admin。审核字段填报单。",
)
def review_field_usage_report(
    tenant_id: int,
    space_id: int,
    report_id: int,
    payload: FieldUsageReportReviewIn,
    reviewer: User = Depends(require_tenant_admin),
    session: Session = Depends(get_session),
):
    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="审核状态仅支持 approved/rejected")
    report = session.get(FieldUsageReport, report_id)
    if not report or report.tenant_id != tenant_id or report.project_space_id != space_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="填报单不存在")
    report.status = payload.status
    report.review_comment = payload.review_comment
    report.reviewed_by_user_id = reviewer.id
    report.reviewed_at = datetime.now(timezone.utc)
    session.add(report)
    session.commit()
    session.refresh(report)
    items = session.exec(
        select(FieldUsageReportItem).where(
            FieldUsageReportItem.tenant_id == tenant_id,
            FieldUsageReportItem.report_id == report.id,
        )
    ).all()
    return FieldUsageReportOut(
        id=report.id,
        tenant_id=report.tenant_id,
        project_space_id=report.project_space_id,
        submitter_user_id=report.submitter_user_id,
        title=report.title,
        status=report.status,
        review_comment=report.review_comment,
        created_at=report.created_at,
        items=[FieldUsageReportItemOut.model_validate(i, from_attributes=True) for i in items],
        behavior_key="field-usage-reports",
    )


@router.get(
    "/tenants/{tenant_id}/spaces/{space_id}/work-orders",
    response_model=Page,
    description="权限：tenant_member / tenant_admin（同项目）或 super_admin。合并待办：待审核字段申请、业务选项申请、字段填报单。",
)
def list_work_orders(
    tenant_id: int,
    space_id: int,
    skip: int = 0,
    limit: int = Query(default=20),
    _: User = Depends(require_tenant_member),
    session: Session = Depends(get_session),
):
    limit = page_limit(limit)
    get_space_or_404(session, tenant_id, space_id)
    frs = session.exec(
        select(FieldRequest).where(
            FieldRequest.tenant_id == tenant_id,
            FieldRequest.project_space_id == space_id,
            FieldRequest.status == "pending",
        )
    ).all()
    ors = session.exec(
        select(BusinessFunctionOptionRequest).where(
            BusinessFunctionOptionRequest.tenant_id == tenant_id,
            BusinessFunctionOptionRequest.project_space_id == space_id,
            BusinessFunctionOptionRequest.status == "pending",
        )
    ).all()
    urs = session.exec(
        select(FieldUsageReport).where(
            FieldUsageReport.tenant_id == tenant_id,
            FieldUsageReport.project_space_id == space_id,
            FieldUsageReport.status == "pending_review",
        )
    ).all()
    merged: list[tuple[datetime, str, object]] = []
    for x in frs:
        merged.append((x.created_at, "field_request", x))
    for x in ors:
        merged.append((x.created_at, "business_option_request", x))
    for x in urs:
        merged.append((x.created_at, "field_usage_report", x))
    merged.sort(key=lambda t: t[0], reverse=True)
    total = len(merged)
    page = merged[skip : skip + limit]
    items_out: list[dict] = []
    for _created_at, kind, obj in page:
        if kind == "field_request":
            items_out.append(
                {
                    "order_kind": "field_request",
                    "id": obj.id,
                    "status": obj.status,
                    "created_at": obj.created_at,
                    "summary": obj.field_name,
                    "requester_user_id": obj.requester_user_id,
                }
            )
        elif kind == "business_option_request":
            items_out.append(
                {
                    "order_kind": "business_option_request",
                    "id": obj.id,
                    "status": obj.status,
                    "created_at": obj.created_at,
                    "summary": obj.option_name,
                    "requester_user_id": obj.requester_user_id,
                }
            )
        else:
            items_out.append(
                {
                    "order_kind": "field_usage_report",
                    "id": obj.id,
                    "status": obj.status,
                    "created_at": obj.created_at,
                    "summary": obj.title or f"填报单#{obj.id}",
                    "submitter_user_id": obj.submitter_user_id,
                }
            )
    return {"total": total, "items": items_out}
