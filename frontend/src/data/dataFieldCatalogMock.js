/**
 * 数据字段主数据（主表选项）— 前端模拟。
 * 数据安全 FO：全量 CRUD + 查看与每条字段关联的业务功能（来自已审核填报中的 data_field × business_function）。
 * 功能 FO：仅见与本账户绑定业务功能相关、且来源于已审核通过填报的字段；新增/删除走申请，由数据安全 FO 在本页审核。
 */

import { loadSubmissionTasksMerged, submissionFunctionName } from "./submissionTasksMock.js";

export const DATA_FIELD_CATALOG_STORAGE_KEY = "dsms_mock_data_field_catalog_v1";
export const DATA_FIELD_CATALOG_REQUESTS_KEY = "dsms_mock_data_field_catalog_requests_v1";

export const DATA_FIELD_CATALOG_PERSIST_EVENT = "dsms-data-field-catalog-persisted";

/** 与生命周期填报列一致 */
export const LIFECYCLE_DATA_FIELD_ROW_KEY = "data_field";
export const LIFECYCLE_BUSINESS_FUNCTION_ROW_KEY = "business_function";

const SEED_LABELS = [
  "主数据字段：客户编号",
  "主数据字段：车辆 VIN",
  "主数据字段：动力总成件号",
  "主数据字段：软件版本号"
];

function bumpListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(DATA_FIELD_CATALOG_PERSIST_EVENT));
  }
}

function buildSeedEntries() {
  const today = new Date().toISOString().slice(0, 10);
  return SEED_LABELS.map((label, i) => ({
    id: `df_${i + 1}`,
    label,
    description: "",
    createdAt: today,
    updatedAt: today
  }));
}

/** @returns {{ id: string, label: string, description: string, createdAt: string, updatedAt: string }[]} */
export function loadDataFieldCatalogEntries() {
  try {
    const raw = sessionStorage.getItem(DATA_FIELD_CATALOG_STORAGE_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (Array.isArray(data) && data.length) return data;
    }
  } catch {
    /* ignore */
  }
  const seed = buildSeedEntries();
  try {
    sessionStorage.setItem(DATA_FIELD_CATALOG_STORAGE_KEY, JSON.stringify(seed));
  } catch {
    /* ignore */
  }
  bumpListeners();
  return seed;
}

/** @param {{ id: string, label: string, description: string, createdAt: string, updatedAt: string }[]} entries */
export function persistDataFieldCatalogEntries(entries) {
  sessionStorage.setItem(DATA_FIELD_CATALOG_STORAGE_KEY, JSON.stringify(entries));
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
 * 仅解析 `foFillLifecycleRows`（与明细表一致）；旧版仅 sections 的快照不计入。
 * @returns {Map<string, Set<string>>}
 */
export function aggregateDataFieldLabelToFunctionIdsFromApprovedSubmissions() {
  const map = new Map();
  const tasks = loadSubmissionTasksMerged();
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
 * 功能 FO 视角：仅保留在「已审核通过」填报中、与本人绑定业务功能有关联的目录项。
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

/** @returns {any[]} */
export function loadCatalogRequests() {
  try {
    const raw = sessionStorage.getItem(DATA_FIELD_CATALOG_REQUESTS_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (Array.isArray(data)) return data;
    }
  } catch {
    /* ignore */
  }
  return [];
}

export function persistCatalogRequests(list) {
  sessionStorage.setItem(DATA_FIELD_CATALOG_REQUESTS_KEY, JSON.stringify(list));
  bumpListeners();
}

let nextReqId = 1;

export function submitCatalogRequest(payload) {
  const list = loadCatalogRequests();
  const id = `dfr_${Date.now()}_${nextReqId++}`;
  list.push({
    id,
    type: payload.type,
    catalogEntryId: payload.catalogEntryId ?? null,
    proposedLabel: String(payload.proposedLabel || "").trim(),
    proposedDescription: String(payload.proposedDescription || "").trim(),
    requestedBy: payload.requestedBy != null ? String(payload.requestedBy).trim() : "",
    requestedAt: new Date().toISOString().slice(0, 16).replace("T", " "),
    status: "pending",
    rejectReason: "",
    reviewedAt: ""
  });
  persistCatalogRequests(list);
  return id;
}

/** @param {{ id: string }[]} entries */
export function generateNextDataFieldCatalogId(entries) {
  let max = 0;
  for (const e of entries) {
    const m = /^df_(\d+)$/.exec(String(e.id || ""));
    if (m) max = Math.max(max, Number(m[1]));
  }
  return `df_${max + 1}`;
}

/**
 * 数据安全侧直接新增（不经申请）。
 * @param {{ label: string, description?: string }} payload
 */
export function addDataFieldCatalogEntryDirect(payload) {
  const lab = String(payload.label || "").trim();
  if (!lab) return { ok: false, message: "数据字段名称不能为空。" };
  const entries = loadDataFieldCatalogEntries();
  if (entries.some((e) => String(e.label || "").trim() === lab)) {
    return { ok: false, message: "已存在同名数据字段。" };
  }
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  const day = now.slice(0, 10);
  entries.push({
    id: generateNextDataFieldCatalogId(entries),
    label: lab,
    description: String(payload.description || "").trim(),
    createdAt: day,
    updatedAt: day
  });
  persistDataFieldCatalogEntries(entries);
  return { ok: true, message: "已新增数据字段。" };
}

/**
 * @param {string} entryId
 * @param {{ label: string, description?: string }} payload
 */
export function updateDataFieldCatalogEntryDirect(entryId, payload) {
  const id = String(entryId || "").trim();
  if (!id) return { ok: false, message: "缺少条目 id。" };
  const lab = String(payload.label || "").trim();
  if (!lab) return { ok: false, message: "数据字段名称不能为空。" };
  const entries = loadDataFieldCatalogEntries();
  const idx = entries.findIndex((e) => e.id === id);
  if (idx < 0) return { ok: false, message: "未找到对应数据字段。" };
  if (entries.some((e, i) => i !== idx && String(e.label || "").trim() === lab)) {
    return { ok: false, message: "已存在同名数据字段。" };
  }
  const now = new Date().toISOString().slice(0, 10);
  entries[idx] = {
    ...entries[idx],
    label: lab,
    description: String(payload.description ?? entries[idx].description ?? "").trim(),
    updatedAt: now
  };
  persistDataFieldCatalogEntries(entries);
  return { ok: true, message: "已保存修改。" };
}

/** @param {string} entryId */
export function removeDataFieldCatalogEntryDirect(entryId) {
  const id = String(entryId || "").trim();
  if (!id) return { ok: false, message: "缺少条目 id。" };
  const entries = loadDataFieldCatalogEntries();
  const next = entries.filter((e) => e.id !== id);
  if (next.length === entries.length) return { ok: false, message: "未找到对应数据字段。" };
  persistDataFieldCatalogEntries(next);
  return { ok: true, message: "已删除数据字段。" };
}

/** 审核通过：新增目录项或删除；并写回 requests */
export function approveCatalogRequest(requestId) {
  const list = loadCatalogRequests();
  const req = list.find((r) => r.id === requestId);
  if (!req || req.status !== "pending") return { ok: false, message: "申请不存在或已处理。" };
  const entries = loadDataFieldCatalogEntries();
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  if (req.type === "create") {
    if (!req.proposedLabel) {
      return { ok: false, message: "申请缺少数据字段名称。" };
    }
    if (entries.some((e) => String(e.label).trim() === req.proposedLabel)) {
      return { ok: false, message: "已存在同名数据字段。" };
    }
    entries.push({
      id: generateNextDataFieldCatalogId(entries),
      label: req.proposedLabel,
      description: req.proposedDescription || "",
      createdAt: now.slice(0, 10),
      updatedAt: now.slice(0, 10)
    });
    persistDataFieldCatalogEntries(entries);
  } else if (req.type === "delete") {
    const id = req.catalogEntryId;
    if (!id) return { ok: false, message: "缺少要删除的条目 id。" };
    const next = entries.filter((e) => e.id !== id);
    if (next.length === entries.length) return { ok: false, message: "未找到对应数据字段。" };
    persistDataFieldCatalogEntries(next);
  } else {
    return { ok: false, message: "未知申请类型。" };
  }
  req.status = "approved";
  req.reviewedAt = now;
  req.rejectReason = "";
  persistCatalogRequests(list);
  return { ok: true, message: "已通过申请。" };
}

export function rejectCatalogRequest(requestId, reason) {
  const list = loadCatalogRequests();
  const req = list.find((r) => r.id === requestId);
  if (!req || req.status !== "pending") return { ok: false, message: "申请不存在或已处理。" };
  req.status = "rejected";
  req.rejectReason = String(reason || "").trim() || "—";
  req.reviewedAt = new Date().toISOString().slice(0, 16).replace("T", " ");
  persistCatalogRequests(list);
  return { ok: true, message: "已驳回申请。" };
}
