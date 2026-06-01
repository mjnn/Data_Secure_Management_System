"""Phase 2/3 路由共享辅助函数。"""

import json

from sqlmodel import Session

from app.models import ClassificationAuditLog


def log_classification_audit(
    session: Session,
    tenant_id: int,
    space_id: int,
    user_id: int,
    behavior_key: str,
    detail: dict | None = None,
) -> None:
    session.add(
        ClassificationAuditLog(
            tenant_id=tenant_id,
            project_space_id=space_id,
            user_id=user_id,
            behavior_key=behavior_key,
            detail_json=json.dumps(detail or {}, ensure_ascii=False),
        )
    )
