/**
 * 填报任务归一化与业务功能名称解析（目录由 portal API 写入缓存）。
 */

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const SUBMISSION_TASKS_STORAGE_KEY = "dsms_mock_submission_tasks_v1";

/** @type {{ id: string, name: string, key: string, functionFoBound: boolean, foDisplay: string }[]} */
let businessFunctionCatalog = [];

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(SUBMISSION_TASKS_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** @param {object[]} functions 来自 fetchBusinessFunctions 的映射行 */
export function setBusinessFunctionCatalog(functions) {
  clearLegacySessionStorage();
  businessFunctionCatalog = (functions || []).map((f) => ({
    id: String(f.id ?? f.function_key ?? f.key ?? ""),
    name: String(f.name || f.id || ""),
    key: String(f.key ?? f.function_key ?? f.id ?? ""),
    functionFoBound: !!(f.functionFoBound ?? f.has_active_fo_binding),
    foDisplay: f.foDisplay ?? (f.requires_fo_binding ? "function_fo" : "")
  }));
}

export function submissionFunctionById(id) {
  return businessFunctionCatalog.find((f) => f.id === id) || null;
}

export function submissionFunctionName(id) {
  return submissionFunctionById(id)?.name || id;
}

export function submissionTaskRowHasBoundFo(row) {
  return !!submissionFunctionById(row.functionId)?.functionFoBound;
}

/** 是否存在可渲染的填报表单只读快照（sections 或 lifecycle 明细表） */
export function hasRenderableFormSnapshot(snapshot) {
  if (!snapshot) return false;
  if (
    snapshot.formTable &&
    Array.isArray(snapshot.formTable.columns) &&
    snapshot.formTable.columns.length &&
    Array.isArray(snapshot.formTable.rows) &&
    snapshot.formTable.rows.length
  ) {
    return true;
  }
  return Array.isArray(snapshot.sections) && snapshot.sections.some((s) => s?.fields?.length);
}

/**
 * @param {object} t
 * @returns {object}
 */
export function normalizeSubmissionTask(t) {
  const row = { ...t };
  if (row.status === "dispatched" && row.foFillStatus == null) {
    row.foFillStatus = "not_started";
  }
  if (row.foCancellationRequested == null) {
    row.foCancellationRequested = false;
  }
  if (row.foCancellationReason == null) {
    row.foCancellationReason = "";
  }
  if (row.auditStatus == null) {
    row.auditStatus = null;
  }
  if (row.auditComment == null) {
    row.auditComment = "";
  }
  if (row.auditedAt == null) {
    row.auditedAt = null;
  }
  if (row.foFillFormSnapshot === undefined) {
    row.foFillFormSnapshot = null;
  }
  if (row.foFillLifecycleRows === undefined) {
    row.foFillLifecycleRows = null;
  }
  if (row.foCancelApprovalPending == null) {
    row.foCancelApprovalPending = false;
  }
  if (row.foWorkflowStep == null) row.foWorkflowStep = null;
  if (row.foRelevanceConclusion == null) row.foRelevanceConclusion = null;
  if (row.foRelevanceFillRow == null) row.foRelevanceFillRow = null;
  if (row.foGovernanceResult == null) row.foGovernanceResult = null;
  return row;
}
