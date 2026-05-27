/**
 * 数据字段主数据 — 只读适配层。
 * 目录数据以 `fetchFieldCatalog` 写入 `spaceConfigCache` 为真源；不再使用 sessionStorage 种子。
 */

import { getPortalTaskCache } from "../api/portalApi.js";
import { getFieldCatalogCache, hasFieldCatalogCache, setFieldCatalogCache } from "../stores/spaceConfigCache.js";
import { submissionFunctionName } from "./submissionTasksMock.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const DATA_FIELD_CATALOG_STORAGE_KEY = "dsms_mock_data_field_catalog_v1";
/** @deprecated */
export const DATA_FIELD_CATALOG_REQUESTS_KEY = "dsms_mock_data_field_catalog_requests_v1";

export const DATA_FIELD_CATALOG_PERSIST_EVENT = "dsms-data-field-catalog-persisted";

/** 与生命周期填报列一致 */
export const LIFECYCLE_DATA_FIELD_ROW_KEY = "data_field";
export const LIFECYCLE_BUSINESS_FUNCTION_ROW_KEY = "business_function";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(DATA_FIELD_CATALOG_STORAGE_KEY);
    sessionStorage.removeItem(DATA_FIELD_CATALOG_REQUESTS_KEY);
  } catch {
    /* ignore */
  }
}

function bumpListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(DATA_FIELD_CATALOG_PERSIST_EVENT));
  }
}

function normalizeCatalogEntry(raw, index) {
  return {
    id: String(raw?.id ?? `df_${index + 1}`),
    label: String(raw?.label || raw?.field_name || "").trim(),
    description: String(raw?.description || "").trim(),
    taxonomy_code: raw?.taxonomy_code != null ? String(raw.taxonomy_code).trim() : "",
    createdAt: raw?.createdAt || raw?.created_at?.slice?.(0, 10) || "",
    updatedAt: raw?.updatedAt || raw?.updated_at?.slice?.(0, 10) || raw?.created_at?.slice?.(0, 10) || "",
    identifier_key: raw?.identifier_key,
    _apiId: raw?._apiId ?? raw?.id
  };
}

/** @returns {ReturnType<normalizeCatalogEntry>[]} */
export function loadDataFieldCatalogEntries() {
  clearLegacySessionStorage();
  if (hasFieldCatalogCache()) {
    return getFieldCatalogCache().map((row, i) => normalizeCatalogEntry(row, i));
  }
  return [];
}

/** 同步内存缓存（供旧 mock 链路写入；不再落 sessionStorage） */
export function persistDataFieldCatalogEntries(entries) {
  setFieldCatalogCache((entries || []).map((row, i) => normalizeCatalogEntry(row, i)));
  bumpListeners();
}

/** 供生命周期内置「数据字段」下拉使用：按 label 排序 */
export function getCatalogLabelsSorted() {
  return [...loadDataFieldCatalogEntries()]
    .map((e) => String(e.label || "").trim())
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));
}

/**
 * 从「已审核通过」的填报任务中汇总：每个数据字段 label → 出现过的业务功能 functionId 集合。
 * @returns {Map<string, Set<string>>}
 */
export function aggregateDataFieldLabelToFunctionIdsFromApprovedSubmissions() {
  const map = new Map();
  const tasks = getPortalTaskCache();
  for (const t of tasks) {
    if (t.auditStatus !== "approved") continue;
    const rows = t.foFillLifecycleRows;
    if (!Array.isArray(rows)) continue;
    for (const row of rows) {
      if (!row || typeof row !== "object") continue;
      const lab = String(row[LIFECYCLE_DATA_FIELD_ROW_KEY] || "").trim();
      const fid = String(row[LIFECYCLE_BUSINESS_FUNCTION_ROW_KEY] || "").trim();
      if (!lab || !fid) continue;
      if (!map.has(lab)) map.set(lab, new Set());
      map.get(lab).add(fid);
    }
  }
  return map;
}

/** @param {string} label */
export function formatRelatedFunctionNames(label) {
  const m = aggregateDataFieldLabelToFunctionIdsFromApprovedSubmissions();
  const set = m.get(label);
  if (!set || !set.size) return "—";
  return [...set].map((id) => submissionFunctionName(id)).join("、");
}

/**
 * 功能 FO 视角：仅保留在「已审核通过」填报中、与绑定业务功能有关联的目录项。
 * @param {string[]} boundFunctionIds
 */
export function filterCatalogEntriesForFunctionFo(boundFunctionIds) {
  const bound = new Set(boundFunctionIds || []);
  const agg = aggregateDataFieldLabelToFunctionIdsFromApprovedSubmissions();
  return loadDataFieldCatalogEntries().filter((e) => {
    const lab = String(e.label || "").trim();
    const fs = agg.get(lab);
    if (!fs || !fs.size) return false;
    for (const fid of fs) {
      if (bound.has(fid)) return true;
    }
    return false;
  });
}
