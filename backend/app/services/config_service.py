"""空间配置导出/导入（约定见 docs/DECISIONS.md D4）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.models import (
    ClassificationMatrix,
    ClassificationRule,
    FieldCatalogEntry,
    GovernanceChangeLog,
    LifecycleFieldConfig,
    ProjectSpace,
    QuestionnaireQuestion,
    RelevanceRule,
    TaxonomyNode,
)


def _row_dict(obj, keys: list[str]) -> dict[str, Any]:
    return {k: getattr(obj, k) for k in keys if hasattr(obj, k)}


def export_space_config(session: Session, tenant_id: int, space_id: int) -> dict[str, Any]:
    tax = session.exec(
        select(TaxonomyNode).where(
            TaxonomyNode.tenant_id == tenant_id, TaxonomyNode.project_space_id == space_id
        )
    ).all()
    qs = session.exec(
        select(QuestionnaireQuestion).where(
            QuestionnaireQuestion.tenant_id == tenant_id,
            QuestionnaireQuestion.project_space_id == space_id,
        )
    ).all()
    lc = session.exec(
        select(LifecycleFieldConfig).where(
            LifecycleFieldConfig.tenant_id == tenant_id,
            LifecycleFieldConfig.project_space_id == space_id,
        )
    ).all()
    fc = session.exec(
        select(FieldCatalogEntry).where(
            FieldCatalogEntry.tenant_id == tenant_id,
            FieldCatalogEntry.project_space_id == space_id,
        )
    ).all()
    mx = session.exec(
        select(ClassificationMatrix).where(
            ClassificationMatrix.tenant_id == tenant_id,
            ClassificationMatrix.project_space_id == space_id,
        )
    ).all()
    ru = session.exec(
        select(ClassificationRule).where(
            ClassificationRule.tenant_id == tenant_id,
            ClassificationRule.project_space_id == space_id,
        )
    ).all()
    rel = session.exec(
        select(RelevanceRule).where(
            RelevanceRule.tenant_id == tenant_id,
            RelevanceRule.project_space_id == space_id,
        )
    ).first()
    return {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_tenant_id": tenant_id,
        "source_project_space_id": space_id,
        "taxonomy_nodes": [
            _row_dict(
                t,
                ["id", "parent_id", "code", "name", "sort_order"],
            )
            for t in tax
        ],
        "questionnaire_questions": [
            _row_dict(
                q,
                ["key", "title", "question_type", "is_required", "sort_order"],
            )
            for q in qs
        ],
        "lifecycle_field_configs": [
            _row_dict(
                x,
                [
                    "field_key",
                    "field_label",
                    "field_type",
                    "is_required",
                    "options_json",
                    "validation_json",
                    "sort_order",
                ],
            )
            for x in lc
        ],
        "field_catalog_entries": [
            _row_dict(
                e,
                [
                    "field_name",
                    "identifier_key",
                    "data_type",
                    "sensitivity_level",
                    "source_system",
                    "taxonomy_code",
                ],
            )
            for e in fc
        ],
        "classification_matrices": [
            _row_dict(m, ["name", "description", "cells_json"]) for m in mx
        ],
        "classification_rules": [
            _row_dict(r, ["name", "priority", "condition_json", "output_sensitivity", "is_active"])
            for r in ru
        ],
        "relevance_rule": _row_dict(rel, ["expression"]) if rel else None,
    }


def import_space_config(
    session: Session,
    target_tenant_id: int,
    target_space_id: int,
    bundle: dict[str, Any],
) -> dict[str, int]:
    """将 bundle 合并进目标空间；返回计数统计。"""
    if bundle.get("version") != 1:
        raise ValueError("不支持的配置包版本")
    space = session.get(ProjectSpace, target_space_id)
    if not space or space.tenant_id != target_tenant_id:
        raise ValueError("目标项目空间不存在")
    counts = {
        "taxonomy_nodes": 0,
        "questionnaire_questions": 0,
        "lifecycle_field_configs": 0,
        "field_catalog_entries": 0,
        "classification_matrices": 0,
        "classification_rules": 0,
        "relevance_rule_updated": 0,
    }
    id_map: dict[int, int] = {}
    nodes_raw = bundle.get("taxonomy_nodes") or []
    remaining: dict[int, dict[str, Any]] = {}
    for n in nodes_raw:
        if isinstance(n, dict) and "id" in n and "code" in n:
            remaining[int(n["id"])] = n
    while remaining:
        batch = [
            oid
            for oid, n in remaining.items()
            if n.get("parent_id") is None or int(n["parent_id"]) in id_map
        ]
        if not batch:
            break
        for oid in batch:
            n = remaining.pop(oid)
            pid = n.get("parent_id")
            new_parent = id_map.get(int(pid)) if pid is not None else None
            exists = session.exec(
                select(TaxonomyNode).where(
                    TaxonomyNode.tenant_id == target_tenant_id,
                    TaxonomyNode.project_space_id == target_space_id,
                    TaxonomyNode.code == n["code"],
                )
            ).first()
            if exists:
                id_map[oid] = exists.id
                continue
            tn = TaxonomyNode(
                tenant_id=target_tenant_id,
                project_space_id=target_space_id,
                parent_id=new_parent,
                code=n["code"],
                name=n["name"],
                sort_order=int(n.get("sort_order") or 0),
            )
            session.add(tn)
            session.flush()
            id_map[oid] = tn.id
            counts["taxonomy_nodes"] += 1
    for q in bundle.get("questionnaire_questions") or []:
        if not isinstance(q, dict) or not q.get("key"):
            continue
        ex = session.exec(
            select(QuestionnaireQuestion).where(
                QuestionnaireQuestion.tenant_id == target_tenant_id,
                QuestionnaireQuestion.project_space_id == target_space_id,
                QuestionnaireQuestion.key == q["key"],
            )
        ).first()
        if ex:
            ex.title = q.get("title") or ex.title
            ex.question_type = q.get("question_type") or ex.question_type
            ex.is_required = bool(q.get("is_required", ex.is_required))
            ex.sort_order = int(q.get("sort_order") or ex.sort_order)
            session.add(ex)
        else:
            session.add(
                QuestionnaireQuestion(
                    tenant_id=target_tenant_id,
                    project_space_id=target_space_id,
                    key=q["key"],
                    title=q.get("title") or "",
                    question_type=q.get("question_type") or "text",
                    is_required=bool(q.get("is_required", False)),
                    sort_order=int(q.get("sort_order") or 0),
                )
            )
            counts["questionnaire_questions"] += 1
    for x in bundle.get("lifecycle_field_configs") or []:
        if not isinstance(x, dict) or not x.get("field_key"):
            continue
        ex = session.exec(
            select(LifecycleFieldConfig).where(
                LifecycleFieldConfig.tenant_id == target_tenant_id,
                LifecycleFieldConfig.project_space_id == target_space_id,
                LifecycleFieldConfig.field_key == x["field_key"],
            )
        ).first()
        if ex:
            for k in ("field_label", "field_type", "is_required", "options_json", "validation_json", "sort_order"):
                if k in x and x[k] is not None:
                    setattr(ex, k, x[k])
            session.add(ex)
        else:
            session.add(
                LifecycleFieldConfig(
                    tenant_id=target_tenant_id,
                    project_space_id=target_space_id,
                    field_key=x["field_key"],
                    field_label=x.get("field_label") or "",
                    field_type=x.get("field_type") or "text",
                    is_required=bool(x.get("is_required", False)),
                    options_json=x.get("options_json"),
                    validation_json=x.get("validation_json"),
                    sort_order=int(x.get("sort_order") or 0),
                )
            )
            counts["lifecycle_field_configs"] += 1
    for e in bundle.get("field_catalog_entries") or []:
        if not isinstance(e, dict) or not e.get("field_name"):
            continue
        ex = session.exec(
            select(FieldCatalogEntry).where(
                FieldCatalogEntry.tenant_id == target_tenant_id,
                FieldCatalogEntry.project_space_id == target_space_id,
                FieldCatalogEntry.field_name == e["field_name"],
            )
        ).first()
        if ex:
            ex.identifier_key = e.get("identifier_key") or ex.identifier_key
            ex.data_type = e.get("data_type") or ex.data_type
            if "sensitivity_level" in e:
                ex.sensitivity_level = e.get("sensitivity_level")
            if "source_system" in e:
                ex.source_system = e.get("source_system")
            if "taxonomy_code" in e:
                ex.taxonomy_code = e.get("taxonomy_code")
            session.add(ex)
        else:
            session.add(
                FieldCatalogEntry(
                    tenant_id=target_tenant_id,
                    project_space_id=target_space_id,
                    field_name=e["field_name"],
                    identifier_key=e.get("identifier_key") or e["field_name"].lower(),
                    data_type=e.get("data_type") or "string",
                    sensitivity_level=e.get("sensitivity_level"),
                    source_system=e.get("source_system"),
                    taxonomy_code=e.get("taxonomy_code"),
                )
            )
            counts["field_catalog_entries"] += 1
    for m in bundle.get("classification_matrices") or []:
        if not isinstance(m, dict) or not m.get("name"):
            continue
        session.add(
            ClassificationMatrix(
                tenant_id=target_tenant_id,
                project_space_id=target_space_id,
                name=m["name"],
                description=m.get("description"),
                cells_json=m.get("cells_json") or "[]",
            )
        )
        counts["classification_matrices"] += 1
    for r in bundle.get("classification_rules") or []:
        if not isinstance(r, dict) or not r.get("name"):
            continue
        session.add(
            ClassificationRule(
                tenant_id=target_tenant_id,
                project_space_id=target_space_id,
                name=r["name"],
                priority=int(r.get("priority") or 100),
                condition_json=r.get("condition_json") or "{}",
                output_sensitivity=r.get("output_sensitivity") or "未分级",
                is_active=bool(r.get("is_active", True)),
            )
        )
        counts["classification_rules"] += 1
    rel = bundle.get("relevance_rule")
    if isinstance(rel, dict) and "expression" in rel:
        ex = session.exec(
            select(RelevanceRule).where(
                RelevanceRule.tenant_id == target_tenant_id,
                RelevanceRule.project_space_id == target_space_id,
            )
        ).first()
        if ex:
            ex.expression = rel.get("expression") or ""
            session.add(ex)
            counts["relevance_rule_updated"] = 1
        else:
            session.add(
                RelevanceRule(
                    tenant_id=target_tenant_id,
                    project_space_id=target_space_id,
                    expression=rel.get("expression") or "",
                )
            )
            counts["relevance_rule_updated"] = 1
    return counts


def governance_log(
    session: Session,
    *,
    tenant_id: int,
    space_id: int,
    user_id: int,
    behavior_key: str,
    resource_type: str | None,
    resource_id: int | None,
    summary: str,
    detail: dict[str, Any] | None = None,
) -> None:
    session.add(
        GovernanceChangeLog(
            tenant_id=tenant_id,
            project_space_id=space_id,
            user_id=user_id,
            behavior_key=behavior_key,
            resource_type=resource_type,
            resource_id=resource_id,
            summary=summary,
            detail_json=json.dumps(detail or {}, ensure_ascii=False),
        )
    )
