"""一次性脚本：将 dsms.py 拆为 dsms_platform.py + dsms_space.py。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "api"
src_lines = (ROOT / "dsms.py").read_text(encoding="utf-8").splitlines(keepends=True)

split_at = None
for i, line in enumerate(src_lines):
    if line.strip() == "@router.get(" and i + 1 < len(src_lines):
        if "/tenants/{tenant_id}/spaces/{space_id}/questionnaires/questions" in src_lines[i + 1]:
            split_at = i
            break

if split_at is None:
    raise SystemExit("split point not found")

COMMON_IMPORTS = '''import csv
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
'''

PLATFORM_MODELS = '''from app.models import (
    ProjectSpace,
    Tenant,
    TenantCreatorAllowlist,
    TenantMembership,
    User,
)
from app.schemas import (
    PlatformUsersBatchDeactivateIn,
    PlatformUsersPlatformRoleIn,
    MemberBatchIn,
    MemberBatchRemoveIn,
    MemberRoleUpdateIn,
    Page,
    SpaceCreateIn,
    SpaceDeleteIn,
    SpaceOut,
    SpaceUpdateIn,
    TenantCreateIn,
    TenantCreatorUpdate,
    TenantOut,
    TenantPatchIn,
    UserImportItem,
    UserDirectoryOut,
)

router = APIRouter(prefix="/api/v1/dsms", tags=["dsms-platform"])
'''

SPACE_MODELS = '''from app.models import (
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
'''

# platform body: from first @router after helpers through line before split
platform_start = None
for i, line in enumerate(src_lines):
    if line.startswith("@router.get") and "/platform/tenant-creators" in src_lines[i + 1]:
        platform_start = i
        break

platform_body = "".join(src_lines[platform_start:split_at])
space_body = "".join(src_lines[split_at:])

(ROOT / "dsms_platform.py").write_text(COMMON_IMPORTS + PLATFORM_MODELS + "\n" + platform_body, encoding="utf-8")
(ROOT / "dsms_space.py").write_text(COMMON_IMPORTS + SPACE_MODELS + "\n" + space_body, encoding="utf-8")
print(f"Wrote dsms_platform.py ({split_at - platform_start} lines) and dsms_space.py ({len(src_lines) - split_at} lines)")
