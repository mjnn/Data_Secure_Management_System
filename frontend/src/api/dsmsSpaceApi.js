/**
 * 空间级配置 API（问卷 / 表达式 / 生命周期 / 分类 / 密级 / 项目）。
 */
import api from "../api";
import { newRelevanceGroupNode, normalizeRelevanceGroup } from "../data/relevanceLogicTree.js";
import { configItemToTableRow } from "../data/lifecycleFieldConfigMock.js";
import {
  setClassGradesCache,
  setLifecycleFieldsCache,
  setQuestionnaireCache,
  setRelevanceExpressionCache,
  setSecurityRulesCache,
  setSensitivityLevelsCache,
  setTaxonomyLevelsCache,
  setTaxonomyNodesCache
} from "../stores/spaceConfigCache.js";
import {
  PORTAL_DATA_REFRESH_EVENT,
  bumpPortalDataListeners,
  fetchBusinessFunctions,
  fetchFieldCatalog
} from "./portalApi.js";

function spaceBase(tenantId, spaceId) {
  return `/api/v1/dsms/tenants/${tenantId}/spaces/${spaceId}`;
}

function parseJson(raw, fallback) {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function mapQuestionFromApi(row) {
  const options = parseJson(row.options_json, []);
  return {
    id: String(row.id),
    _apiId: row.id,
    key: row.key,
    title: row.title,
    sort_order: row.sort_order ?? 0,
    options: Array.isArray(options)
      ? options.map((o, i) => ({
          id: String(o.id || `qo_${row.id}_${i}`),
          label: String(o.label || ""),
          sort_order: o.sort_order ?? i
        }))
      : [],
    createdAt: row.created_at?.slice?.(0, 10) || "",
    updatedAt: row.updated_at?.slice?.(0, 10) || row.created_at?.slice?.(0, 10) || ""
  };
}

function optionsToJson(options) {
  return JSON.stringify(
    (options || []).map((o, i) => ({
      id: o.id || `qo_${Date.now()}_${i}`,
      label: String(o.label || "").trim(),
      sort_order: i
    })),
    null,
    0
  );
}

const INPUT_TYPE_MAP = {
  text: "text",
  textarea: "textarea",
  single_select: "single_select",
  multi_select: "multi_select"
};

function mapLifecycleFromApi(row) {
  const allowed = parseJson(row.options_json, []);
  const validation = parseJson(row.validation_json, {});
  const inputType = INPUT_TYPE_MAP[row.field_type] || row.field_type || "text";
  return configItemToTableRow({
    id: row.id,
    field_key: row.field_key,
    label: row.field_label,
    input_type: inputType,
    is_builtin: !!row.is_builtin,
    sort_order: row.sort_order ?? 0,
    help_text: validation.help_text || null,
    required: !!row.is_required,
    min_length: validation.min_length ?? null,
    max_length: validation.max_length ?? null,
    regex_pattern: validation.regex_pattern ?? null,
    regex_error_message: validation.regex_error_message ?? null,
    allowed_values: Array.isArray(allowed) ? allowed : []
  });
}

function lifecycleRowToApi(row) {
  const validation = {};
  if (row.min_length != null) validation.min_length = Number(row.min_length);
  if (row.max_length != null) validation.max_length = Number(row.max_length);
  if (row.regex_pattern) validation.regex_pattern = row.regex_pattern;
  if (row.regex_error_message) validation.regex_error_message = row.regex_error_message;
  if (row.help_text) validation.help_text = row.help_text;
  const opts =
    row.input_type === "single_select" || row.input_type === "multi_select"
      ? (row.allowed_values || []).filter(Boolean)
      : null;
  return {
    field_key: row.field_key,
    field_label: row.label,
    field_type: row.input_type || "text",
    is_required: !!row.required,
    options_json: opts?.length ? JSON.stringify(opts) : null,
    validation_json: Object.keys(validation).length ? JSON.stringify(validation) : null,
    sort_order: row.sort_order ?? 0
  };
}

function mapExpressionFromApi(data) {
  if (!data?.expression) {
    return {
      logic_root: newRelevanceGroupNode(),
      conclusionWhenTrue: "relevant",
      conclusionWhenFalse: "irrelevant",
      updatedAt: new Date().toISOString().slice(0, 10)
    };
  }
  const parsed = parseJson(data.expression, null);
  if (parsed && typeof parsed === "object" && parsed.logic_root) {
    return {
      logic_root: normalizeRelevanceGroup(parsed.logic_root),
      conclusionWhenTrue: parsed.conclusionWhenTrue === "irrelevant" ? "irrelevant" : "relevant",
      conclusionWhenFalse: parsed.conclusionWhenFalse === "relevant" ? "relevant" : "irrelevant",
      updatedAt: parsed.updatedAt || new Date().toISOString().slice(0, 10)
    };
  }
  return {
    logic_root: newRelevanceGroupNode(),
    conclusionWhenTrue: "relevant",
    conclusionWhenFalse: "irrelevant",
    updatedAt: new Date().toISOString().slice(0, 10)
  };
}

// --- Tenants ---

export async function fetchTenants(skip = 0, limit = 100) {
  const { data } = await api.get("/api/v1/dsms/tenants", { params: { skip, limit } });
  return (data?.items || []).map((t) => ({
    id: t.id,
    name: t.name,
    slug: t.slug || "",
    createdAt: t.created_at?.slice?.(0, 10) || ""
  }));
}

export async function createTenant(body) {
  const { data } = await api.post("/api/v1/dsms/tenants", body);
  bumpPortalDataListeners();
  return data;
}

export async function deleteTenant(tenantId) {
  const { data } = await api.delete(`/api/v1/dsms/tenants/${tenantId}`);
  bumpPortalDataListeners();
  return data;
}

/** 将来源空间内已审核通过的填报任务复制到目标空间（新建项目勾选） */
export async function copyApprovedSubmissionTasks(
  targetTenantId,
  targetSpaceId,
  sourceTenantId,
  sourceSpaceId
) {
  const { data } = await api.post(
    `${spaceBase(targetTenantId, targetSpaceId)}/submission-tasks/copy-approved-from`,
    {
      source_tenant_id: sourceTenantId,
      source_project_space_id: sourceSpaceId
    }
  );
  bumpPortalDataListeners();
  return data;
}

export async function importTenantSeeds(tenantId) {
  const { data } = await api.post(`/api/v1/dsms/tenants/${tenantId}/seeds/import`);
  bumpPortalDataListeners();
  return data;
}

export async function exportSpaceConfig(tenantId, spaceId) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/config/export`);
  return data?.bundle || data;
}

export async function importSpaceConfigToTarget(sourceTenantId, sourceSpaceId, bundle, targetTenantId, targetSpaceId) {
  const { data } = await api.post(`${spaceBase(sourceTenantId, sourceSpaceId)}/config/import`, {
    bundle,
    target_tenant_id: targetTenantId,
    target_project_space_id: targetSpaceId
  });
  bumpPortalDataListeners();
  return data;
}

export async function fetchSpaces(tenantId, skip = 0, limit = 50) {
  const { data } = await api.get(`/api/v1/dsms/tenants/${tenantId}/spaces`, { params: { skip, limit } });
  return data?.items || [];
}

// --- Questionnaire ---

export async function fetchQuestionnaireQuestions(tenantId, spaceId) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/questionnaires/questions`, {
    params: { skip: 0, limit: 500 }
  });
  const items = (data?.items || []).map(mapQuestionFromApi).sort((a, b) => a.sort_order - b.sort_order);
  setQuestionnaireCache(items);
  return items;
}

export async function createQuestionnaireQuestion(tenantId, spaceId, body) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/questionnaires/questions`, {
    key: body.key,
    title: body.title,
    question_type: "single_select",
    is_required: true,
    sort_order: body.sort_order ?? 0,
    options_json: optionsToJson(body.options)
  });
  bumpPortalDataListeners();
  return mapQuestionFromApi(data);
}

export async function updateQuestionnaireQuestion(tenantId, spaceId, body) {
  const { data } = await api.put(`${spaceBase(tenantId, spaceId)}/questionnaires/questions`, {
    id: body._apiId || Number(body.id),
    title: body.title,
    question_type: "single_select",
    is_required: true,
    sort_order: body.sort_order ?? 0,
    options_json: optionsToJson(body.options)
  });
  bumpPortalDataListeners();
  return mapQuestionFromApi(data);
}

export async function deleteQuestionnaireQuestions(tenantId, spaceId, ids) {
  const numIds = ids.map((id) => Number(id)).filter((n) => Number.isFinite(n));
  await api.post(`${spaceBase(tenantId, spaceId)}/questionnaires/questions/delete`, { ids: numIds });
  bumpPortalDataListeners();
}

// --- Relevance expression ---

export async function fetchRelevanceExpression(tenantId, spaceId) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/relevance/rules`);
  const expr = mapExpressionFromApi(data);
  setRelevanceExpressionCache(expr);
  return expr;
}

export async function saveRelevanceExpression(tenantId, spaceId, expr) {
  const payload = JSON.stringify({
    logic_root: expr.logic_root,
    conclusionWhenTrue: expr.conclusionWhenTrue,
    conclusionWhenFalse: expr.conclusionWhenFalse,
    updatedAt: new Date().toISOString().slice(0, 10)
  });
  await api.put(`${spaceBase(tenantId, spaceId)}/relevance/rules`, { expression: payload });
  setRelevanceExpressionCache(expr);
  bumpPortalDataListeners();
}

// --- Lifecycle field config ---

export async function fetchLifecycleFieldConfig(tenantId, spaceId) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/forms/lifecycle-field-config`, {
    params: { skip: 0, limit: 500 }
  });
  const items = (data?.items || []).map(mapLifecycleFromApi).sort((a, b) => a.sort_order - b.sort_order);
  setLifecycleFieldsCache(items);
  return items;
}

export async function createLifecycleField(tenantId, spaceId, row) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/forms/lifecycle-field-config`, lifecycleRowToApi(row));
  bumpPortalDataListeners();
  return mapLifecycleFromApi(data);
}

export async function updateLifecycleField(tenantId, spaceId, row) {
  const { data } = await api.put(
    `${spaceBase(tenantId, spaceId)}/forms/lifecycle-field-config`,
    lifecycleRowToApi(row),
    { params: { id: row.id } }
  );
  bumpPortalDataListeners();
  return mapLifecycleFromApi(data);
}

export async function deleteLifecycleField(tenantId, spaceId, id) {
  await api.delete(`${spaceBase(tenantId, spaceId)}/forms/lifecycle-field-config`, { params: { id } });
  bumpPortalDataListeners();
}

export async function syncLifecycleFieldConfigTable(tenantId, spaceId, rows) {
  const existing = await fetchLifecycleFieldConfig(tenantId, spaceId);
  const existingByKey = new Map(existing.map((r) => [r.field_key, r]));
  const nextKeys = new Set(rows.map((r) => r.field_key));
  for (const row of rows) {
    const prev = existingByKey.get(row.field_key);
    if (prev?.id) {
      await updateLifecycleField(tenantId, spaceId, { ...row, id: prev.id });
    } else if (!row.is_builtin) {
      await createLifecycleField(tenantId, spaceId, row);
    } else if (prev?.id) {
      await updateLifecycleField(tenantId, spaceId, { ...row, id: prev.id });
    }
  }
  for (const ex of existing) {
    if (!ex.is_builtin && !nextKeys.has(ex.field_key)) {
      await deleteLifecycleField(tenantId, spaceId, ex.id);
    }
  }
  return fetchLifecycleFieldConfig(tenantId, spaceId);
}

// --- Taxonomy nodes ---

export async function fetchTaxonomyNodes(tenantId, spaceId) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/taxonomy/nodes`, { params: { skip: 0, limit: 500 } });
  const items = (data?.items || []).map((n) => ({
    id: String(n.id),
    _apiId: n.id,
    code: n.code,
    name: n.name,
    parent_id: n.parent_id != null ? String(n.parent_id) : null,
    sort_order: n.sort_order ?? 0
  }));
  setTaxonomyNodesCache(items);
  return items;
}

export async function createTaxonomyNode(tenantId, spaceId, body) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/taxonomy/nodes`, {
    code: body.code,
    name: body.name,
    parent_id: body.parent_id ? Number(body.parent_id) : null,
    sort_order: body.sort_order ?? 0
  });
  bumpPortalDataListeners();
  return {
    id: String(data.id),
    _apiId: data.id,
    code: data.code,
    name: data.name,
    parent_id: data.parent_id != null ? String(data.parent_id) : null,
    sort_order: data.sort_order ?? 0
  };
}

export async function updateTaxonomyNode(tenantId, spaceId, nodeId, body) {
  const { data } = await api.put(`${spaceBase(tenantId, spaceId)}/taxonomy/nodes/${Number(nodeId)}`, {
    code: body.code,
    name: body.name,
    parent_id: body.parent_id ? Number(body.parent_id) : null,
    sort_order: body.sort_order ?? 0
  });
  bumpPortalDataListeners();
  return {
    id: String(data.id),
    _apiId: data.id,
    code: data.code,
    name: data.name,
    parent_id: data.parent_id != null ? String(data.parent_id) : null,
    sort_order: data.sort_order ?? 0
  };
}

export async function deleteTaxonomyNode(tenantId, spaceId, nodeId) {
  await api.delete(`${spaceBase(tenantId, spaceId)}/taxonomy/nodes/${Number(nodeId)}`);
  bumpPortalDataListeners();
}

// --- Taxonomy levels ---

function mapTaxonomyLevelFromApi(row) {
  return {
    id: String(row.id),
    _apiId: row.id,
    level: row.level ?? 0,
    name: row.name || "",
    description: row.description || "",
    sort_order: row.sort_order ?? 0,
    updatedAt: row.updated_at?.slice?.(0, 10) || ""
  };
}

export async function fetchTaxonomyLevels(tenantId, spaceId) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/taxonomy-levels`, {
    params: { skip: 0, limit: 100 }
  });
  const items = (data?.items || []).map(mapTaxonomyLevelFromApi);
  setTaxonomyLevelsCache(items);
  return items;
}

export async function createTaxonomyLevel(tenantId, spaceId, body) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/taxonomy-levels`, body);
  bumpPortalDataListeners();
  return mapTaxonomyLevelFromApi(data);
}

export async function updateTaxonomyLevel(tenantId, spaceId, levelId, body) {
  const { data } = await api.put(`${spaceBase(tenantId, spaceId)}/taxonomy-levels/${Number(levelId)}`, body);
  bumpPortalDataListeners();
  return mapTaxonomyLevelFromApi(data);
}

export async function deleteTaxonomyLevel(tenantId, spaceId, levelId) {
  await api.delete(`${spaceBase(tenantId, spaceId)}/taxonomy-levels/${Number(levelId)}`);
  bumpPortalDataListeners();
}

// --- Sensitivity levels ---

export async function fetchSensitivityLevels(tenantId, spaceId) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/sensitivity-levels`, {
    params: { skip: 0, limit: 100 }
  });
  const items = (data?.items || []).map((s) => ({
    id: String(s.id),
    code: s.code,
    label: s.label,
    description: s.description || "",
    sort_order: s.sort_order ?? 0
  }));
  setSensitivityLevelsCache(items);
  return items;
}

// --- Field class grade ---

function mapClassGradeFromApi(row) {
  return {
    field_catalog_entry_id: String(row.field_catalog_entry_id),
    grade_label: row.grade_label || "",
    notes: row.notes || "",
    updatedAt: row.updated_at?.slice?.(0, 10) || ""
  };
}

export async function fetchFieldClassGrades(tenantId, spaceId) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/fields/class-grade`, {
    params: { skip: 0, limit: 500 }
  });
  const items = (data?.items || []).map(mapClassGradeFromApi);
  setClassGradesCache(items);
  return items;
}

export async function putFieldClassGrades(tenantId, spaceId, grades) {
  await api.put(`${spaceBase(tenantId, spaceId)}/fields/class-grade`, {
    grades: grades.map((g) => ({
      field_catalog_entry_id: Number(g.field_catalog_entry_id),
      grade_label: g.grade_label,
      notes: g.notes || null
    }))
  });
  bumpPortalDataListeners();
  return fetchFieldClassGrades(tenantId, spaceId);
}

export async function deleteFieldClassGrade(tenantId, spaceId, catalogEntryId) {
  await api.delete(`${spaceBase(tenantId, spaceId)}/fields/class-grade/${Number(catalogEntryId)}`);
  bumpPortalDataListeners();
}

// --- Security requirements ---

const PORTAL_RULE_KIND = "portal_rule";

function mapSecurityRuleFromApi(row) {
  let portal = {};
  try {
    portal = JSON.parse(row.check_json || "{}");
  } catch {
    portal = {};
  }
  if (row.check_kind === PORTAL_RULE_KIND && portal.trigger_root) {
    return {
      id: String(row.id),
      _apiId: row.id,
      rule_name: row.requirement_name,
      trigger_root: portal.trigger_root,
      action: portal.action || { content_html: "", is_active: true },
      updatedAt: row.updated_at?.slice?.(0, 10) || row.created_at?.slice?.(0, 10) || "",
      field_catalog_entry_id: row.field_catalog_entry_id
    };
  }
  return {
    id: String(row.id),
    _apiId: row.id,
    rule_name: row.requirement_name,
    check_kind: row.check_kind,
    check_json: row.check_json,
    is_active: row.is_active,
    field_catalog_entry_id: row.field_catalog_entry_id,
    updatedAt: row.updated_at?.slice?.(0, 10) || ""
  };
}

function portalRuleToApiBody(rule, anchorFieldId) {
  return {
    field_catalog_entry_id: Number(anchorFieldId),
    requirement_name: rule.rule_name,
    check_kind: PORTAL_RULE_KIND,
    check_json: JSON.stringify({
      trigger_root: rule.trigger_root,
      action: rule.action
    }),
    is_active: rule.action?.is_active !== false
  };
}

export async function fetchSecurityRequirements(tenantId, spaceId) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/fields/security-requirements`, {
    params: { skip: 0, limit: 500 }
  });
  const items = (data?.items || []).map(mapSecurityRuleFromApi);
  setSecurityRulesCache(items);
  return items;
}

export async function createSecurityRequirementRule(tenantId, spaceId, rule, anchorFieldId) {
  const { data } = await api.post(
    `${spaceBase(tenantId, spaceId)}/fields/security-requirements`,
    portalRuleToApiBody(rule, anchorFieldId)
  );
  bumpPortalDataListeners();
  return mapSecurityRuleFromApi(data);
}

export async function updateSecurityRequirementRule(tenantId, spaceId, requirementId, rule) {
  const { data } = await api.put(
    `${spaceBase(tenantId, spaceId)}/fields/security-requirements/${Number(requirementId)}`,
    {
      requirement_name: rule.rule_name,
      check_kind: PORTAL_RULE_KIND,
      check_json: JSON.stringify({
        trigger_root: rule.trigger_root,
        action: rule.action
      }),
      is_active: rule.action?.is_active !== false
    }
  );
  bumpPortalDataListeners();
  return mapSecurityRuleFromApi(data);
}

export async function deleteSecurityRequirementRule(tenantId, spaceId, requirementId) {
  await api.delete(`${spaceBase(tenantId, spaceId)}/fields/security-requirements/${Number(requirementId)}`);
  bumpPortalDataListeners();
}

export async function evaluateSecurityRequirements(tenantId, spaceId, fieldCatalogEntryIds) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/fields/security-requirements/evaluate`, {
    field_catalog_entry_ids: fieldCatalogEntryIds?.length ? fieldCatalogEntryIds.map(Number) : null
  });
  return data;
}

// --- Users (platform) ---

export async function fetchUsersDirectory(params = {}) {
  const { data } = await api.get("/api/v1/dsms/users", {
    params: { skip: 0, limit: 500, ...params }
  });
  return data;
}

export async function fetchTenantMembers(tenantId, skip = 0, limit = 500) {
  const { data } = await api.get(`/api/v1/dsms/tenants/${tenantId}/members`, { params: { skip, limit } });
  return data?.items || [];
}

export async function batchAddTenantMembers(tenantId, userIds) {
  const { data } = await api.post(`/api/v1/dsms/tenants/${tenantId}/members/batch`, { user_ids: userIds });
  return data;
}

export async function batchRemoveTenantMembers(tenantId, userIds) {
  const { data } = await api.post(`/api/v1/dsms/tenants/${tenantId}/members/batch-remove`, { user_ids: userIds });
  return data;
}

export async function setTenantMemberRole(tenantId, userId, role) {
  const { data } = await api.put(`/api/v1/dsms/tenants/${tenantId}/members/${userId}/role`, { role });
  return data;
}

export async function downloadUserImportTemplate() {
  return api.get("/api/v1/dsms/platform/users/import-excel/template", { responseType: "blob" });
}

export async function importUsersExcel(file) {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await api.post("/api/v1/dsms/platform/users/import-excel", fd, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function fetchTenantCreators() {
  const { data } = await api.get("/api/v1/dsms/platform/tenant-creators");
  return data;
}

export async function updateTenantCreators(userIds) {
  const { data } = await api.put("/api/v1/dsms/platform/tenant-creators", { user_ids: userIds });
  return data;
}

export async function batchDeactivateUsers(userIds) {
  const { data } = await api.post("/api/v1/dsms/platform/users/batch-deactivate", { user_ids: userIds });
  return data;
}

export async function batchSetPlatformRole(userIds, platformRole) {
  const { data } = await api.put("/api/v1/dsms/platform/users/batch-platform-role", {
    user_ids: userIds,
    platform_role: platformRole
  });
  return data;
}

// --- Classification (phase 2) ---

export async function fetchClassificationMatrices(tenantId, spaceId, skip = 0, limit = 500) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/classification/matrix`, {
    params: { skip, limit }
  });
  return data;
}

export async function createClassificationMatrix(tenantId, spaceId, body) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/classification/matrix`, body);
  return data;
}

export async function updateClassificationMatrix(tenantId, spaceId, body) {
  const { data } = await api.put(`${spaceBase(tenantId, spaceId)}/classification/matrix`, body);
  return data;
}

export async function deleteClassificationMatrix(tenantId, spaceId, matrixId) {
  const { data } = await api.delete(
    `${spaceBase(tenantId, spaceId)}/classification/matrix/${Number(matrixId)}`
  );
  return data;
}

export async function fetchClassificationRules(tenantId, spaceId, skip = 0, limit = 500) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/classification/rules`, {
    params: { skip, limit }
  });
  return data;
}

export async function createClassificationRule(tenantId, spaceId, body) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/classification/rules`, body);
  return data;
}

export async function updateClassificationRule(tenantId, spaceId, body) {
  const { data } = await api.put(`${spaceBase(tenantId, spaceId)}/classification/rules`, body);
  return data;
}

export async function deleteClassificationRule(tenantId, spaceId, ruleId) {
  const { data } = await api.delete(
    `${spaceBase(tenantId, spaceId)}/classification/rules/${Number(ruleId)}`
  );
  return data;
}

export async function fetchClassificationResults(tenantId, spaceId, skip = 0, limit = 500) {
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/classification/results`, {
    params: { skip, limit }
  });
  return data;
}

export async function classificationRecompute(tenantId, spaceId) {
  const { data } = await api.post(`${spaceBase(tenantId, spaceId)}/classification/recompute`);
  bumpPortalDataListeners();
  return data;
}

export async function classificationManualOverride(tenantId, spaceId, resultId, body) {
  const { data } = await api.put(
    `${spaceBase(tenantId, spaceId)}/classification/results/${Number(resultId)}/manual`,
    body
  );
  bumpPortalDataListeners();
  return data;
}

export async function classificationRevertAuto(tenantId, spaceId, resultId) {
  const { data } = await api.post(
    `${spaceBase(tenantId, spaceId)}/classification/results/${Number(resultId)}/revert-auto`
  );
  bumpPortalDataListeners();
  return data;
}

export async function fetchClassificationAudit(tenantId, spaceId, skip = 0, limit = 20, behaviorKey = null) {
  const params = { skip, limit };
  if (behaviorKey) params.behavior_key = behaviorKey;
  const { data } = await api.get(`${spaceBase(tenantId, spaceId)}/classification/audit`, { params });
  return data;
}

export async function downloadClassificationExportCsv(tenantId, spaceId) {
  const res = await api.get(`${spaceBase(tenantId, spaceId)}/classification/export`, {
    responseType: "blob"
  });
  return res;
}

/** 拉取工作流依赖的配置并写入 cache */
export async function bootstrapSpaceConfig(tenantId, spaceId) {
  await Promise.all([
    fetchBusinessFunctions(tenantId, spaceId).catch(() => []),
    fetchQuestionnaireQuestions(tenantId, spaceId).catch(() => []),
    fetchRelevanceExpression(tenantId, spaceId).catch(() => null),
    fetchLifecycleFieldConfig(tenantId, spaceId).catch(() => []),
    fetchSensitivityLevels(tenantId, spaceId).catch(() => []),
    fetchTaxonomyLevels(tenantId, spaceId).catch(() => []),
    fetchTaxonomyNodes(tenantId, spaceId).catch(() => []),
    fetchFieldCatalog(tenantId, spaceId).catch(() => []),
    fetchFieldClassGrades(tenantId, spaceId).catch(() => []),
    fetchSecurityRequirements(tenantId, spaceId).catch(() => [])
  ]);
}

export { PORTAL_DATA_REFRESH_EVENT };
