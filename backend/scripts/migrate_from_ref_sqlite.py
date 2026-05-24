#!/usr/bin/env python3
"""
将 ref/data_secure_from_rds.sqlite（旧「工具 + project_space」模型）迁移到当前 DSMS SQLite 模型。

映射约定（见同目录说明）：
- 源库 `tool_id` -> 目标库新建项目 `slug=migrated-ref-tool-{tool_id}`，`tenant_id` 即该项目主键。
- 源 `datasecureprojectspace` -> `projectspace`（保留 `space_key` / `name`），并建立 `old_project_space_id -> new_id`。
- 源 `datasecurequestionnairequestion` -> `questionnairequestion`（`question_key` -> `key`）。
- 源 `datasecurerelevancerule` -> `relevancerule`（结构化字段序列化进 `expression` JSON）。
- 源 `datasecurelifecyclefielddefinition` + `datasecurelifecyclefieldconfig` -> `lifecyclefieldconfig`（按 `field_key` 合并）。
- 源 `datasecuregovernancechangelog` -> `governancechangelog`（`behavior_key` 使用平台迁移键）。

用法（在 backend 目录）：
  python scripts/migrate_from_ref_sqlite.py --ref ../ref/data_secure_from_rds.sqlite
  python scripts/migrate_from_ref_sqlite.py --ref ../ref/data_secure_from_rds.sqlite --dry-run

依赖：与后端相同的 PYTHONPATH（在 backend 下执行即可）。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import engine
from app.models import (
    GovernanceChangeLog,
    LifecycleFieldConfig,
    ProjectSpace,
    QuestionnaireQuestion,
    RelevanceRule,
    Tenant,
    TenantMembership,
    User,
)


def _parse_dt(v) -> datetime:
    now = datetime.now(timezone.utc)
    if v is None:
        return now
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).strip()
    if not s:
        return now
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s.replace(" ", "T"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return now


def _norm_question_type(t: str | None) -> str:
    if not t:
        return "text"
    x = str(t).strip().upper()
    if x in ("YES_NO", "BOOLEAN"):
        return "yes_no"
    if x in ("TEXTAREA",):
        return "textarea"
    return str(t).lower()


def _map_field_type(input_type: str | None) -> str:
    if not input_type:
        return "text"
    x = str(input_type).strip().upper()
    if x == "TEXTAREA":
        return "textarea"
    if x in ("YES_NO", "BOOLEAN"):
        return "yes_no"
    if x == "SELECT":
        return "select"
    return "text"


def _first_superuser_id(session: Session) -> int:
    u = session.exec(select(User).where(User.is_superuser == True)).first()  # noqa: E712
    if not u:
        raise SystemExit("目标库中不存在 is_superuser 用户，请先启动过一次后端以种子超管。")
    return u.id


def migrate(ref_path: Path, dry_run: bool) -> None:
    src = sqlite3.connect(str(ref_path))
    src.row_factory = sqlite3.Row

    with Session(engine) as session:
        admin_id = _first_superuser_id(session)

        # --- tenants from distinct tool_id in project spaces ---
        tool_rows = list(src.execute("SELECT DISTINCT tool_id FROM datasecureprojectspace").fetchall())
        tool_id_to_tenant_id: dict[int, int] = {}

        for (tid,) in tool_rows:
            tid = int(tid)
            slug = f"migrated-ref-tool-{tid}"
            existing = session.exec(select(Tenant).where(Tenant.slug == slug)).first()
            if existing:
                tool_id_to_tenant_id[tid] = existing.id
                mem = session.exec(
                    select(TenantMembership).where(
                        TenantMembership.tenant_id == existing.id,
                        TenantMembership.user_id == admin_id,
                    )
                ).first()
                if not mem and not dry_run:
                    session.add(TenantMembership(tenant_id=existing.id, user_id=admin_id, role="tenant_admin"))
                print(f"tenant exists slug={slug} id={existing.id}")
                continue
            trow = src.execute("SELECT name FROM tool WHERE id = ?", (tid,)).fetchone()
            tname = (trow["name"] if trow else f"migrated-tool-{tid}")[:100]
            if dry_run:
                print(f"[dry-run] would create Tenant name={tname!r} slug={slug}")
                tool_id_to_tenant_id[tid] = -tid
                continue
            tenant = Tenant(name=f"[迁移] {tname}", slug=slug)
            session.add(tenant)
            session.flush()
            tool_id_to_tenant_id[tid] = tenant.id
            session.add(TenantMembership(tenant_id=tenant.id, user_id=admin_id, role="tenant_admin"))
            print(f"created tenant id={tenant.id} slug={slug}")

        if dry_run:
            print("[dry-run] stopping before writes")
            return

        session.commit()

        # reload mapping for real ids after commit
        for (tid,) in tool_rows:
            tid = int(tid)
            slug = f"migrated-ref-tool-{tid}"
            t = session.exec(select(Tenant).where(Tenant.slug == slug)).first()
            if t:
                tool_id_to_tenant_id[tid] = t.id

        old_ps_to_new: dict[int, int] = {}

        for row in src.execute("SELECT * FROM datasecureprojectspace").fetchall():
            tid = int(row["tool_id"])
            tenant_id = tool_id_to_tenant_id[tid]
            old_id = int(row["id"])
            sk = str(row["space_key"] or f"space-{old_id}")[:200]
            nm = str(row["name"] or sk)[:200]
            clash = session.exec(
                select(ProjectSpace).where(ProjectSpace.tenant_id == tenant_id, ProjectSpace.space_key == sk)
            ).first()
            if clash:
                sk = f"{sk}-m{old_id}"[:200]
            ps = ProjectSpace(tenant_id=tenant_id, space_key=sk, name=nm)
            session.add(ps)
            session.flush()
            old_ps_to_new[old_id] = ps.id
            print(f"projectspace old={old_id} -> new={ps.id} tenant={tenant_id} key={sk!r}")

        for row in src.execute("SELECT * FROM datasecurequestionnairequestion").fetchall():
            old_ps = int(row["project_space_id"])
            if old_ps not in old_ps_to_new:
                print(f"skip question id={row['id']}: unknown project_space_id={old_ps}")
                continue
            tenant_id = tool_id_to_tenant_id[int(row["tool_id"])]
            new_ps = old_ps_to_new[old_ps]
            key = str(row["question_key"] or "")[:200]
            title = str(row["title"] or key)[:500]
            qq = QuestionnaireQuestion(
                tenant_id=tenant_id,
                project_space_id=new_ps,
                key=key,
                title=title,
                question_type=_norm_question_type(row["question_type"]),
                is_required=bool(row["is_required"]),
                sort_order=int(row["sort_order"] or 0),
                created_at=_parse_dt(row["created_at"]),
                updated_at=_parse_dt(row["updated_at"]),
            )
            dup = session.exec(
                select(QuestionnaireQuestion).where(
                    QuestionnaireQuestion.tenant_id == tenant_id,
                    QuestionnaireQuestion.project_space_id == new_ps,
                    QuestionnaireQuestion.key == key,
                )
            ).first()
            if dup:
                print(f"skip duplicate question key={key!r} space={new_ps}")
                continue
            session.add(qq)
            print(f"question key={key!r} -> space {new_ps}")

        for row in src.execute("SELECT * FROM datasecurerelevancerule").fetchall():
            old_ps = int(row["project_space_id"])
            if old_ps not in old_ps_to_new:
                continue
            tenant_id = tool_id_to_tenant_id[int(row["tool_id"])]
            new_ps = old_ps_to_new[old_ps]
            payload = {
                "legacy_min_yes_count": int(row["min_yes_count"] or 0),
                "legacy_logic_operator": row["logic_operator"],
                "legacy_question_keys_json": row["question_keys_json"],
                "legacy_logic_expression": row["logic_expression"],
                "legacy_notes": row["notes"],
            }
            expr = json.dumps(payload, ensure_ascii=False)
            existing = session.exec(
                select(RelevanceRule).where(
                    RelevanceRule.tenant_id == tenant_id, RelevanceRule.project_space_id == new_ps
                )
            ).first()
            if existing:
                existing.expression = expr
                existing.updated_at = _parse_dt(row["updated_at"])
                session.add(existing)
            else:
                session.add(
                    RelevanceRule(
                        tenant_id=tenant_id,
                        project_space_id=new_ps,
                        expression=expr,
                        updated_at=_parse_dt(row["updated_at"]),
                    )
                )
            print(f"relevance rule -> space {new_ps}")

        # lifecycle: merge definition + config by (tool_id, project_space_id, field_key)
        defs = list(src.execute("SELECT * FROM datasecurelifecyclefielddefinition").fetchall())
        cfgs = { (int(r["tool_id"]), int(r["project_space_id"]), str(r["field_key"])): r for r in src.execute("SELECT * FROM datasecurelifecyclefieldconfig").fetchall() }

        seen_keys: set[tuple[int, int, str]] = set()
        for d in defs:
            tid = int(d["tool_id"])
            old_ps = int(d["project_space_id"])
            if old_ps not in old_ps_to_new:
                continue
            tenant_id = tool_id_to_tenant_id[tid]
            new_ps = old_ps_to_new[old_ps]
            fk = str(d["field_key"] or "")[:200]
            if not fk:
                continue
            seen_keys.add((tenant_id, new_ps, fk))
            cfg = cfgs.get((tid, old_ps, fk))
            val: dict = {}
            if cfg:
                if cfg["min_length"] is not None:
                    val["minLength"] = cfg["min_length"]
                if cfg["max_length"] is not None:
                    val["maxLength"] = cfg["max_length"]
                if cfg["regex_pattern"]:
                    val["pattern"] = str(cfg["regex_pattern"])
                if cfg["regex_error_message"]:
                    val["patternMessage"] = str(cfg["regex_error_message"])
            req = bool(cfg["required"]) if cfg is not None and cfg["required"] is not None else False
            lfc = LifecycleFieldConfig(
                tenant_id=tenant_id,
                project_space_id=new_ps,
                field_key=fk,
                field_label=str(d["label"] or fk)[:500],
                field_type=_map_field_type(d["input_type"]),
                is_required=req,
                options_json=str(cfg["allowed_values_json"]) if cfg and cfg["allowed_values_json"] else None,
                validation_json=json.dumps(val, ensure_ascii=False) if val else None,
                sort_order=int(d["sort_order"] or 0),
                created_at=_parse_dt(d["created_at"]),
                updated_at=_parse_dt(d["updated_at"]),
            )
            ex = session.exec(
                select(LifecycleFieldConfig).where(
                    LifecycleFieldConfig.tenant_id == tenant_id,
                    LifecycleFieldConfig.project_space_id == new_ps,
                    LifecycleFieldConfig.field_key == fk,
                )
            ).first()
            if ex:
                print(f"skip duplicate lifecycle def {fk!r}")
                continue
            session.add(lfc)
            print(f"lifecycle def {fk!r} -> space {new_ps}")

        for c in src.execute("SELECT * FROM datasecurelifecyclefieldconfig").fetchall():
            tid = int(c["tool_id"])
            old_ps = int(c["project_space_id"])
            if old_ps not in old_ps_to_new:
                continue
            fk = str(c["field_key"] or "")[:200]
            if not fk:
                continue
            tenant_id = tool_id_to_tenant_id[tid]
            new_ps = old_ps_to_new[old_ps]
            if (tenant_id, new_ps, fk) in seen_keys:
                continue
            val = {}
            if c["min_length"] is not None:
                val["minLength"] = c["min_length"]
            if c["max_length"] is not None:
                val["maxLength"] = c["max_length"]
            if c["regex_pattern"]:
                val["pattern"] = str(c["regex_pattern"])
            ex = session.exec(
                select(LifecycleFieldConfig).where(
                    LifecycleFieldConfig.tenant_id == tenant_id,
                    LifecycleFieldConfig.project_space_id == new_ps,
                    LifecycleFieldConfig.field_key == fk,
                )
            ).first()
            if ex:
                continue
            req_c = bool(c["required"]) if c["required"] is not None else False
            session.add(
                LifecycleFieldConfig(
                    tenant_id=tenant_id,
                    project_space_id=new_ps,
                    field_key=fk,
                    field_label=fk,
                    field_type="text",
                    is_required=req_c,
                    options_json=str(c["allowed_values_json"]) if c["allowed_values_json"] else None,
                    validation_json=json.dumps(val, ensure_ascii=False) if val else None,
                    sort_order=0,
                    created_at=_parse_dt(c["updated_at"]),
                    updated_at=_parse_dt(c["updated_at"]),
                )
            )
            print(f"lifecycle cfg-only {fk!r} -> space {new_ps}")

        gov_n = 0
        for row in src.execute("SELECT * FROM datasecuregovernancechangelog").fetchall():
            old_ps = int(row["project_space_id"])
            if old_ps not in old_ps_to_new:
                continue
            tenant_id = tool_id_to_tenant_id[int(row["tool_id"])]
            new_ps = old_ps_to_new[old_ps]
            tid_user = int(row["changed_by"]) if row["changed_by"] is not None else admin_id
            if not session.get(User, tid_user):
                tid_user = admin_id
            target_id = row["target_id"]
            rid = None
            if target_id is not None and str(target_id).strip().isdigit():
                rid = int(str(target_id).strip())
            summary = f"{row['domain']}:{row['action']}"
            detail = {
                "legacy_domain": row["domain"],
                "legacy_action": row["action"],
                "legacy_target_type": row["target_type"],
                "legacy_target_id": row["target_id"],
                "legacy_change_reason": row["change_reason"],
                "legacy_detail": row["detail_json"],
            }
            session.add(
                GovernanceChangeLog(
                    tenant_id=tenant_id,
                    project_space_id=new_ps,
                    user_id=tid_user,
                    behavior_key="dsms-ref-sqlite-migration",
                    resource_type=str(row["target_type"])[:100] if row["target_type"] else None,
                    resource_id=rid,
                    summary=summary[:500],
                    detail_json=json.dumps(detail, ensure_ascii=False),
                    created_at=_parse_dt(row["created_at"]),
                )
            )
            gov_n += 1
        print(f"governance rows written: {gov_n}")

        session.commit()
        print("done commit.")


def main() -> None:
    ap = argparse.ArgumentParser(description="从 ref SQLite 迁移到当前 DSMS 库")
    ap.add_argument(
        "--ref",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "ref" / "data_secure_from_rds.sqlite",
        help="源 SQLite 路径",
    )
    ap.add_argument("--dry-run", action="store_true", help="只打印将执行的操作，不写目标库")
    args = ap.parse_args()
    if not args.ref.is_file():
        raise SystemExit(f"源库不存在: {args.ref}")
    print(f"目标 DATABASE_URL={settings.database_url}")
    print(f"源库 {args.ref}")
    migrate(args.ref, args.dry_run)


if __name__ == "__main__":
    main()
