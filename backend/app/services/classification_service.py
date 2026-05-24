"""分类分级重算与安全要求求值（行为约定见 docs/DECISIONS.md）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.models import (
    ClassificationMatrix,
    ClassificationResult,
    ClassificationRule,
    FieldCatalogEntry,
    FieldClassGrade,
    FieldSecurityRequirement,
)


GRADE_RANK: dict[str, int] = {"公开": 0, "内部": 1, "秘密": 2, "机密": 3, "绝密": 4, "未分级": -1}


def grade_rank(label: str | None) -> int:
    if not label:
        return -1
    return GRADE_RANK.get(label.strip(), -1)


def rule_matches(condition: dict[str, Any], entry: FieldCatalogEntry) -> bool:
    t = condition.get("type") or ""
    if t == "default":
        return True
    if t == "identifier_contains":
        v = (condition.get("value") or "").lower()
        return v in (entry.identifier_key or "").lower()
    if t == "field_name_contains":
        v = (condition.get("value") or "").lower()
        return v in (entry.field_name or "").lower()
    if t == "data_type_equals":
        return (condition.get("value") or "") == (entry.data_type or "")
    return False


def parse_condition(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def merge_matrix_levels(session: Session, tenant_id: int, space_id: int) -> dict[str, str]:
    """taxonomy_code -> sensitivity_level，后出现的矩阵覆盖先出现的同 code。"""
    out: dict[str, str] = {}
    matrices = session.exec(
        select(ClassificationMatrix)
        .where(
            ClassificationMatrix.tenant_id == tenant_id,
            ClassificationMatrix.project_space_id == space_id,
        )
        .order_by(ClassificationMatrix.id.asc())
    ).all()
    for m in matrices:
        try:
            cells = json.loads(m.cells_json or "[]")
        except json.JSONDecodeError:
            continue
        if not isinstance(cells, list):
            continue
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            code = cell.get("taxonomy_code")
            lev = cell.get("sensitivity_level")
            if code and lev:
                out[str(code)] = str(lev)
    return out


def recompute_space(session: Session, tenant_id: int, space_id: int) -> tuple[int, list[int]]:
    """返回 (更新条数, 涉及的 field_catalog_entry_id 列表)。"""
    entries = session.exec(
        select(FieldCatalogEntry).where(
            FieldCatalogEntry.tenant_id == tenant_id,
            FieldCatalogEntry.project_space_id == space_id,
        )
    ).all()
    rules = session.exec(
        select(ClassificationRule)
        .where(
            ClassificationRule.tenant_id == tenant_id,
            ClassificationRule.project_space_id == space_id,
            ClassificationRule.is_active == True,  # noqa: E712
        )
        .order_by(ClassificationRule.priority.asc(), ClassificationRule.id.asc())
    ).all()
    matrix_map = merge_matrix_levels(session, tenant_id, space_id)
    updated_ids: list[int] = []
    now = datetime.now(timezone.utc)
    for entry in entries:
        level = entry.sensitivity_level or "未分级"
        matched_rule_id = None
        applied_matrix = False
        for rule in rules:
            cond = parse_condition(rule.condition_json)
            if rule_matches(cond, entry):
                level = rule.output_sensitivity or level
                matched_rule_id = rule.id
                break
        if entry.taxonomy_code and entry.taxonomy_code in matrix_map:
            level = matrix_map[entry.taxonomy_code]
            applied_matrix = True
        expl = {
            "initial_from_catalog": entry.sensitivity_level or "未分级",
            "final_level": level,
            "matched_rule_id": matched_rule_id,
            "applied_matrix": applied_matrix,
            "taxonomy_code": entry.taxonomy_code,
        }
        existing = session.exec(
            select(ClassificationResult).where(
                ClassificationResult.tenant_id == tenant_id,
                ClassificationResult.project_space_id == space_id,
                ClassificationResult.field_catalog_entry_id == entry.id,
            )
        ).first()
        if existing and existing.is_manual_override:
            continue
        if existing:
            existing.sensitivity_level = level
            existing.matched_rule_id = matched_rule_id
            existing.applied_matrix = applied_matrix
            existing.explanation_json = json.dumps(expl, ensure_ascii=False)
            existing.last_recompute_at = now
            existing.updated_at = now
            session.add(existing)
        else:
            session.add(
                ClassificationResult(
                    tenant_id=tenant_id,
                    project_space_id=space_id,
                    field_catalog_entry_id=entry.id,
                    sensitivity_level=level,
                    matched_rule_id=matched_rule_id,
                    applied_matrix=applied_matrix,
                    explanation_json=json.dumps(expl, ensure_ascii=False),
                    last_recompute_at=now,
                    updated_at=now,
                )
            )
        updated_ids.append(entry.id)
    return len(updated_ids), updated_ids


def recompute_single_entry(session: Session, tenant_id: int, space_id: int, field_catalog_entry_id: int) -> None:
    entry = session.get(FieldCatalogEntry, field_catalog_entry_id)
    if not entry or entry.tenant_id != tenant_id or entry.project_space_id != space_id:
        return
    rules = session.exec(
        select(ClassificationRule)
        .where(
            ClassificationRule.tenant_id == tenant_id,
            ClassificationRule.project_space_id == space_id,
            ClassificationRule.is_active == True,  # noqa: E712
        )
        .order_by(ClassificationRule.priority.asc(), ClassificationRule.id.asc())
    ).all()
    matrix_map = merge_matrix_levels(session, tenant_id, space_id)
    level = entry.sensitivity_level or "未分级"
    matched_rule_id = None
    applied_matrix = False
    for rule in rules:
        cond = parse_condition(rule.condition_json)
        if rule_matches(cond, entry):
            level = rule.output_sensitivity or level
            matched_rule_id = rule.id
            break
    if entry.taxonomy_code and entry.taxonomy_code in matrix_map:
        level = matrix_map[entry.taxonomy_code]
        applied_matrix = True
    expl = {
        "initial_from_catalog": entry.sensitivity_level or "未分级",
        "final_level": level,
        "matched_rule_id": matched_rule_id,
        "applied_matrix": applied_matrix,
        "taxonomy_code": entry.taxonomy_code,
    }
    now = datetime.now(timezone.utc)
    existing = session.exec(
        select(ClassificationResult).where(
            ClassificationResult.tenant_id == tenant_id,
            ClassificationResult.project_space_id == space_id,
            ClassificationResult.field_catalog_entry_id == entry.id,
        )
    ).first()
    if existing:
        existing.sensitivity_level = level
        existing.matched_rule_id = matched_rule_id
        existing.applied_matrix = applied_matrix
        existing.is_manual_override = False
        existing.manual_level = None
        existing.manual_reason = None
        existing.manual_by_user_id = None
        existing.manual_at = None
        existing.explanation_json = json.dumps(expl, ensure_ascii=False)
        existing.last_recompute_at = now
        existing.updated_at = now
        session.add(existing)


def evaluate_security_for_entries(
    session: Session, tenant_id: int, space_id: int, entry_ids: list[int] | None
) -> list[dict[str, Any]]:
    q = select(FieldCatalogEntry).where(
        FieldCatalogEntry.tenant_id == tenant_id,
        FieldCatalogEntry.project_space_id == space_id,
    )
    if entry_ids:
        q = q.where(FieldCatalogEntry.id.in_(entry_ids))
    entries = session.exec(q).all()
    out: list[dict[str, Any]] = []
    for entry in entries:
        reqs = session.exec(
            select(FieldSecurityRequirement).where(
                FieldSecurityRequirement.tenant_id == tenant_id,
                FieldSecurityRequirement.project_space_id == space_id,
                FieldSecurityRequirement.field_catalog_entry_id == entry.id,
                FieldSecurityRequirement.is_active == True,  # noqa: E712
            )
        ).all()
        fg = session.exec(
            select(FieldClassGrade).where(
                FieldClassGrade.tenant_id == tenant_id,
                FieldClassGrade.project_space_id == space_id,
                FieldClassGrade.field_catalog_entry_id == entry.id,
            )
        ).first()
        current_grade = fg.grade_label if fg else None
        details: list[dict[str, Any]] = []
        all_pass = True
        for req in reqs:
            try:
                chk = json.loads(req.check_json or "{}")
            except json.JSONDecodeError:
                chk = {}
            passed = True
            reason = ""
            if req.check_kind == "min_grade":
                need = str(chk.get("min_label") or "")
                if grade_rank(current_grade) < grade_rank(need):
                    passed = False
                    reason = f"当前密级「{current_grade or '未设置'}」低于要求「{need}」"
                else:
                    reason = f"密级满足：{current_grade or '未设置'} ≥ {need}"
            elif req.check_kind == "max_length":
                mx = int(chk.get("max") or 0)
                ln = len(entry.identifier_key or "")
                if ln > mx:
                    passed = False
                    reason = f"标识键长度 {ln} 超过上限 {mx}"
                else:
                    reason = f"标识键长度 {ln} 未超过 {mx}"
            else:
                passed = False
                reason = f"不支持的 check_kind：{req.check_kind}"
            if not passed:
                all_pass = False
            details.append(
                {
                    "requirement_id": req.id,
                    "requirement_name": req.requirement_name,
                    "check_kind": req.check_kind,
                    "passed": passed,
                    "reason": reason,
                }
            )
        out.append(
            {
                "field_catalog_entry_id": entry.id,
                "field_name": entry.field_name,
                "current_grade_label": current_grade,
                "passed": all_pass if reqs else True,
                "requirements": details,
            }
        )
    return out
