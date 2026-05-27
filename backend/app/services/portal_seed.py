"""默认项目/空间/业务功能等种子（对齐前端 mock 演示数据）。"""

import json

from sqlmodel import Session, select

from app.models import (
    FieldCatalogEntry,
    LifecycleFieldConfig,
    ProjectSpace,
    QuestionnaireQuestion,
    RelevanceRule,
    SensitivityLevel,
    Tenant,
    TenantMembership,
    User,
)
from app.models_portal import BusinessFunction, FoUserFunctionBinding, SubmissionTask, TaxonomyLevel

DEFAULT_TENANT_SLUG = "default"
DEFAULT_SPACE_KEY = "default"

BUSINESS_FUNCTION_SEED = [
    {"function_key": "field_usage", "name": "字段填报", "requires_fo_binding": True, "sort_order": 1},
    {"function_key": "usage_report", "name": "用量上报", "requires_fo_binding": False, "sort_order": 2},
    {"function_key": "field_request", "name": "字段申请", "requires_fo_binding": True, "sort_order": 3},
]

SENSITIVITY_SEED = [
    {"code": "public", "label": "公开", "sort_order": 0},
    {"code": "internal", "label": "内部", "sort_order": 1},
    {"code": "secret", "label": "秘密", "sort_order": 2},
    {"code": "confidential", "label": "机密", "sort_order": 3},
]

TAXONOMY_LEVEL_SEED = [
    {"level": 0, "name": "根级", "description": "分类树根节点层级", "sort_order": 0},
    {"level": 1, "name": "一级", "description": "", "sort_order": 1},
    {"level": 2, "name": "二级", "description": "", "sort_order": 2},
    {"level": 3, "name": "三级", "description": "", "sort_order": 3},
]

LIFECYCLE_BUILTIN = [
    {"field_key": "data_field", "field_label": "数据字段", "field_type": "text", "is_builtin": True, "sort_order": 0},
    {
        "field_key": "business_function",
        "field_label": "业务功能",
        "field_type": "text",
        "is_builtin": True,
        "sort_order": 1,
    },
]


def ensure_portal_seed(session: Session) -> None:
    tenant = session.exec(select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG)).first()
    if not tenant:
        tenant = Tenant(name="默认项目", slug=DEFAULT_TENANT_SLUG, is_archived=False)
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

    space = session.exec(
        select(ProjectSpace).where(
            ProjectSpace.tenant_id == tenant.id,
            ProjectSpace.space_key == DEFAULT_SPACE_KEY,
        )
    ).first()
    if not space:
        space = ProjectSpace(tenant_id=tenant.id, space_key=DEFAULT_SPACE_KEY, name="默认空间")
        session.add(space)
        session.commit()
        session.refresh(space)

    users = session.exec(select(User)).all()
    for u in users:
        mem = session.exec(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant.id,
                TenantMembership.user_id == u.id,
            )
        ).first()
        if not mem:
            role = "tenant_admin" if u.is_superuser else "tenant_member"
            session.add(TenantMembership(tenant_id=tenant.id, user_id=u.id, role=role))

    functions: dict[str, BusinessFunction] = {}
    for row in BUSINESS_FUNCTION_SEED:
        fn = session.exec(
            select(BusinessFunction).where(
                BusinessFunction.tenant_id == tenant.id,
                BusinessFunction.project_space_id == space.id,
                BusinessFunction.function_key == row["function_key"],
            )
        ).first()
        if not fn:
            fn = BusinessFunction(
                tenant_id=tenant.id,
                project_space_id=space.id,
                function_key=row["function_key"],
                name=row["name"],
                requires_fo_binding=row["requires_fo_binding"],
                sort_order=row["sort_order"],
            )
            session.add(fn)
            session.flush()
        functions[row["function_key"]] = fn

    function_fo = session.exec(select(User).where(User.username == "function_fo")).first()
    if function_fo:
        for key in ("field_usage", "field_request"):
            fn = functions.get(key)
            if not fn:
                continue
            binding = session.exec(
                select(FoUserFunctionBinding).where(
                    FoUserFunctionBinding.tenant_id == tenant.id,
                    FoUserFunctionBinding.project_space_id == space.id,
                    FoUserFunctionBinding.user_id == function_fo.id,
                    FoUserFunctionBinding.business_function_id == fn.id,
                )
            ).first()
            if not binding:
                session.add(
                    FoUserFunctionBinding(
                        tenant_id=tenant.id,
                        project_space_id=space.id,
                        user_id=function_fo.id,
                        business_function_id=fn.id,
                        status="active",
                    )
                )

    for row in TAXONOMY_LEVEL_SEED:
        exists = session.exec(
            select(TaxonomyLevel).where(
                TaxonomyLevel.tenant_id == tenant.id,
                TaxonomyLevel.project_space_id == space.id,
                TaxonomyLevel.level == row["level"],
            )
        ).first()
        if not exists:
            session.add(
                TaxonomyLevel(
                    tenant_id=tenant.id,
                    project_space_id=space.id,
                    level=row["level"],
                    name=row["name"],
                    description=row["description"] or None,
                    sort_order=row["sort_order"],
                )
            )

    for row in SENSITIVITY_SEED:
        exists = session.exec(
            select(SensitivityLevel).where(
                SensitivityLevel.tenant_id == tenant.id,
                SensitivityLevel.project_space_id == space.id,
                SensitivityLevel.code == row["code"],
            )
        ).first()
        if not exists:
            session.add(
                SensitivityLevel(
                    tenant_id=tenant.id,
                    project_space_id=space.id,
                    code=row["code"],
                    label=row["label"],
                    sort_order=row["sort_order"],
                )
            )

    for row in LIFECYCLE_BUILTIN:
        exists = session.exec(
            select(LifecycleFieldConfig).where(
                LifecycleFieldConfig.tenant_id == tenant.id,
                LifecycleFieldConfig.project_space_id == space.id,
                LifecycleFieldConfig.field_key == row["field_key"],
            )
        ).first()
        if not exists:
            session.add(
                LifecycleFieldConfig(
                    tenant_id=tenant.id,
                    project_space_id=space.id,
                    field_key=row["field_key"],
                    field_label=row["field_label"],
                    field_type=row["field_type"],
                    is_builtin=row["is_builtin"],
                    sort_order=row["sort_order"],
                )
            )

    if not session.exec(
        select(FieldCatalogEntry).where(
            FieldCatalogEntry.tenant_id == tenant.id,
            FieldCatalogEntry.project_space_id == space.id,
        )
    ).first():
        session.add(
            FieldCatalogEntry(
                tenant_id=tenant.id,
                project_space_id=space.id,
                field_name="用户手机号",
                description="示例字段",
                identifier_key="user_mobile",
                data_type="string",
            )
        )
        session.add(
            FieldCatalogEntry(
                tenant_id=tenant.id,
                project_space_id=space.id,
                field_name="车辆 VIN",
                description="示例字段",
                identifier_key="vehicle_vin",
                data_type="string",
            )
        )

    if not session.exec(
        select(SubmissionTask).where(
            SubmissionTask.tenant_id == tenant.id,
            SubmissionTask.project_space_id == space.id,
        )
    ).first():
        fn = functions.get("field_usage")
        sec_fo = session.exec(select(User).where(User.username == "security_fo")).first()
        if fn and sec_fo:
            session.add(
                SubmissionTask(
                    tenant_id=tenant.id,
                    project_space_id=space.id,
                    business_function_id=fn.id,
                    title="2026 Q1 字段填报（示例）",
                    internal_note="种子任务",
                    status="dispatched",
                    dispatch_note="请完成功能数据安全相关性判定与生命周期填报。",
                    fo_fill_status="not_started",
                    created_by_user_id=sec_fo.id,
                    assignee_user_id=function_fo.id if function_fo else None,
                )
            )

    _seed_questionnaire(session, tenant.id, space.id)
    _seed_relevance_rule(session, tenant.id, space.id)

    session.commit()


def _seed_questionnaire(session: Session, tenant_id: int, space_id: int) -> None:
    if session.exec(
        select(QuestionnaireQuestion).where(
            QuestionnaireQuestion.tenant_id == tenant_id,
            QuestionnaireQuestion.project_space_id == space_id,
        )
    ).first():
        return
    samples = [
        {
            "key": "involves_personal_data",
            "title": "该业务功能处理的数据是否可能包含个人信息？",
            "sort_order": 0,
            "options": [
                {"id": "qo_1_1", "label": "是", "sort_order": 0},
                {"id": "qo_1_2", "label": "否", "sort_order": 1},
                {"id": "qo_1_3", "label": "不确定", "sort_order": 2},
            ],
        },
        {
            "key": "cross_border_access",
            "title": "该业务功能是否存在跨境或境外访问数据的场景？",
            "sort_order": 1,
            "options": [
                {"id": "qo_2_1", "label": "是", "sort_order": 0},
                {"id": "qo_2_2", "label": "否", "sort_order": 1},
            ],
        },
    ]
    for row in samples:
        session.add(
            QuestionnaireQuestion(
                tenant_id=tenant_id,
                project_space_id=space_id,
                key=row["key"],
                title=row["title"],
                question_type="single_select",
                is_required=True,
                sort_order=row["sort_order"],
                options_json=json.dumps(row["options"], ensure_ascii=False),
            )
        )


def _seed_relevance_rule(session: Session, tenant_id: int, space_id: int) -> None:
    if session.exec(
        select(RelevanceRule).where(
            RelevanceRule.tenant_id == tenant_id,
            RelevanceRule.project_space_id == space_id,
        )
    ).first():
        return
    default_expr = json.dumps(
        {
            "logic_root": {"type": "group", "operator": "and", "children": []},
            "conclusionWhenTrue": "relevant",
            "conclusionWhenFalse": "irrelevant",
        },
        ensure_ascii=False,
    )
    session.add(
        RelevanceRule(
            tenant_id=tenant_id,
            project_space_id=space_id,
            expression=default_expr,
        )
    )
