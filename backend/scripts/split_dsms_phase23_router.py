"""一次性脚本：将 dsms_phase23.py 拆为 classification / fields / governance。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "api"
lines = (ROOT / "dsms_phase23.py").read_text(encoding="utf-8").splitlines(keepends=True)

# 去掉原文件头部到 router 定义，以及 log_classification_audit 函数块
header_end = None
class_grade_start = None
security_start = None
governance_start = None

for i, line in enumerate(lines):
    if line.strip() == "# --- field class grade ---":
        class_grade_start = i
    elif line.strip() == "# --- security requirements ---":
        security_start = i
    elif line.strip() == "# --- Phase 3 governance & config ---":
        governance_start = i
    if line.strip().startswith("router = APIRouter"):
        header_end = i + 1

if not all([header_end, class_grade_start, governance_start]):
    raise SystemExit("split markers not found")

# 原 imports（去掉 json 仅用于 audit 时可保留）、去掉 log_classification_audit
IMPORTS_CLASSIFICATION = '''"""Phase 2 分类矩阵、规则、结果与审计。"""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from app.api.dsms_helpers import get_space_or_404, page_limit
from app.api.dsms_phase23_helpers import log_classification_audit
from app.core.deps import require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import (
    ClassificationAuditLog,
    ClassificationMatrix,
    ClassificationResult,
    ClassificationRule,
    FieldCatalogEntry,
    User,
)
from app.schemas import (
    ClassificationAuditOut,
    ClassificationManualIn,
    ClassificationMatrixBatchImportIn,
    ClassificationMatrixCreateIn,
    ClassificationMatrixOut,
    ClassificationMatrixUpdateIn,
    ClassificationResultOut,
    ClassificationRuleCreateIn,
    ClassificationRuleOut,
    ClassificationRuleUpdateIn,
    Page,
)
from app.services.classification_service import recompute_single_entry, recompute_space
from app.services.config_service import governance_log

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-phase23-classification"])

'''

IMPORTS_FIELDS = '''"""Phase 2/3 字段密级绑定与安全要求。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from app.api.dsms_helpers import get_space_or_404, page_limit
from app.core.deps import require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import FieldCatalogEntry, FieldClassGrade, FieldSecurityRequirement, User
from app.schemas import (
    FieldClassGradeOut,
    FieldClassGradePutIn,
    FieldSecurityEvalIn,
    FieldSecurityEvalItemOut,
    FieldSecurityEvalOut,
    FieldSecurityRequirementCreateIn,
    FieldSecurityRequirementOut,
    FieldSecurityRequirementUpdateIn,
    Page,
)
from app.services.classification_service import evaluate_security_for_entries
from app.services.config_service import governance_log

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-phase23-fields"])

'''

IMPORTS_GOVERNANCE = '''"""Phase 3 治理日志、配置导入导出与合并导出。"""

import csv
import io
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from app.api.dsms_helpers import get_space_or_404, page_limit
from app.core.deps import require_tenant_admin, require_tenant_member
from app.core.database import get_session
from app.models import (
    ClassificationMatrix,
    ClassificationResult,
    ClassificationRule,
    FieldCatalogEntry,
    FieldUsageReport,
    FieldUsageReportItem,
    GovernanceChangeLog,
    User,
)
from app.schemas import ConfigBatchDeleteIn, ConfigImportIn, GovernanceChangeLogOut, Page
from app.services.config_service import export_space_config, governance_log, import_space_config

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-phase23-governance"])

'''

# body starts after "# --- classification matrix ---" (line after log_classification_audit block)
matrix_marker = None
for i, line in enumerate(lines):
    if line.strip() == "# --- classification matrix ---":
        matrix_marker = i
        break

classification_body = "".join(lines[matrix_marker:class_grade_start])
fields_body = "".join(lines[class_grade_start:governance_start])
governance_body = "".join(lines[governance_start:])

(ROOT / "dsms_phase23_classification.py").write_text(
    IMPORTS_CLASSIFICATION + "\n" + classification_body, encoding="utf-8"
)
(ROOT / "dsms_phase23_fields.py").write_text(IMPORTS_FIELDS + "\n" + fields_body, encoding="utf-8")
(ROOT / "dsms_phase23_governance.py").write_text(IMPORTS_GOVERNANCE + "\n" + governance_body, encoding="utf-8")
print("split complete")
