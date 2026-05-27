/**
 * 密级定义 — 只读适配层；真源 `fetchSensitivityLevels`。
 */

import { getSensitivityLevelsCache, hasSensitivityLevelsCache, setSensitivityLevelsCache } from "../stores/spaceConfigCache.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const SENSITIVITY_LEVEL_STORAGE_KEY = "dsms_mock_sensitivity_levels_v1";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(SENSITIVITY_LEVEL_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
export const SENSITIVITY_LEVEL_PERSIST_EVENT = "dsms-sensitivity-levels-persisted";

function bumpListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(SENSITIVITY_LEVEL_PERSIST_EVENT));
  }
}

/** @param {any} raw @param {number} index */
function normalizeLevel(raw, index) {
  return {
    id: String(raw?.id || `sl_${index}`),
    code: String(raw?.code || "").trim(),
    label: String(raw?.label || "").trim(),
    description: String(raw?.description || "").trim(),
    sort_order: typeof raw?.sort_order === "number" ? raw.sort_order : index,
    updatedAt: raw?.updatedAt || new Date().toISOString().slice(0, 10)
  };
}

export function loadSensitivityLevels() {
  clearLegacySessionStorage();
  if (hasSensitivityLevelsCache()) {
    return getSensitivityLevelsCache()
      .map((row, i) => normalizeLevel(row, i))
      .sort((a, b) => a.sort_order - b.sort_order || a.label.localeCompare(b.label, "zh-Hans-CN"));
  }
  return [];
}

function persistSensitivityLevels(list, silent = false) {
  const sorted = [...list]
    .map((row, i) => normalizeLevel(row, i))
    .sort((a, b) => a.sort_order - b.sort_order);
  const normalized = sorted.map((row, i) => ({ ...row, sort_order: i }));
  setSensitivityLevelsCache(normalized);
  if (!silent) bumpListeners();
  return normalized;
}

let nextId = 1;

export function generateSensitivityLevelId() {
  return `sl_${Date.now()}_${nextId++}`;
}

export function listSensitivityLevelLabels() {
  return loadSensitivityLevels().map((r) => r.label);
}

/** @param {string} label */
export function getSensitivityLevelByLabel(label) {
  const lab = String(label || "").trim();
  return loadSensitivityLevels().find((r) => r.label === lab) || null;
}

/**
 * @param {{ code: string, label: string, description?: string }} payload
 */
export function addSensitivityLevel(payload) {
  const code = String(payload.code || "").trim();
  const label = String(payload.label || "").trim();
  if (!code) return { ok: false, message: "请输入密级 code。" };
  if (!label) return { ok: false, message: "请输入密级名称。" };
  const list = loadSensitivityLevels();
  if (list.some((r) => r.code === code)) return { ok: false, message: `密级 code「${code}」已存在。` };
  if (list.some((r) => r.label === label)) return { ok: false, message: `密级名称「${label}」已存在。` };
  list.push({
    id: generateSensitivityLevelId(),
    code,
    label,
    description: String(payload.description || "").trim(),
    sort_order: list.length,
    updatedAt: new Date().toISOString().slice(0, 10)
  });
  persistSensitivityLevels(list);
  return { ok: true, message: "已新增密级。" };
}

/**
 * @param {string} id
 * @param {{ code: string, label: string, description?: string }} payload
 */
export function updateSensitivityLevel(id, payload) {
  const rowId = String(id || "").trim();
  if (!rowId) return { ok: false, message: "缺少密级 id。" };
  const code = String(payload.code || "").trim();
  const label = String(payload.label || "").trim();
  if (!code) return { ok: false, message: "请输入密级 code。" };
  if (!label) return { ok: false, message: "请输入密级名称。" };
  const list = loadSensitivityLevels();
  const idx = list.findIndex((r) => r.id === rowId);
  if (idx < 0) return { ok: false, message: "未找到该密级。" };
  if (list.some((r, i) => i !== idx && r.code === code)) {
    return { ok: false, message: `密级 code「${code}」已被占用。` };
  }
  const oldLabel = list[idx].label;
  if (list.some((r, i) => i !== idx && r.label === label)) {
    return { ok: false, message: `密级名称「${label}」已被占用。` };
  }
  list[idx] = {
    ...list[idx],
    code,
    label,
    description: String(payload.description ?? list[idx].description ?? "").trim(),
    updatedAt: new Date().toISOString().slice(0, 10)
  };
  persistSensitivityLevels(list);
  if (oldLabel !== label) {
    return { ok: true, message: "已保存。若已有字段绑定旧名称，请至「数据字段绑定」页检查并更新。", relabel: { from: oldLabel, to: label } };
  }
  return { ok: true, message: "已保存修改。" };
}

/**
 * @param {string} id
 * @param {(label: string) => number} [countBindingsByLabel]
 */
export function removeSensitivityLevel(id, countBindingsByLabel) {
  const rowId = String(id || "").trim();
  const list = loadSensitivityLevels();
  const row = list.find((r) => r.id === rowId);
  if (!row) return { ok: false, message: "未找到该密级。" };
  if (typeof countBindingsByLabel === "function") {
    const n = countBindingsByLabel(row.label);
    if (n > 0) return { ok: false, message: `仍有 ${n} 个数据字段绑定密级「${row.label}」，无法删除。` };
  }
  persistSensitivityLevels(list.filter((r) => r.id !== rowId));
  return { ok: true, message: "已删除密级。" };
}

/** @param {string} id @param {'up' | 'down'} direction */
export function moveSensitivityLevel(id, direction) {
  const rowId = String(id || "").trim();
  const list = loadSensitivityLevels().sort((a, b) => a.sort_order - b.sort_order);
  const idx = list.findIndex((r) => r.id === rowId);
  if (idx < 0) return { ok: false, message: "未找到该密级。" };
  const target = direction === "up" ? idx - 1 : idx + 1;
  if (target < 0 || target >= list.length) {
    return { ok: false, message: direction === "up" ? "已在最上级。" : "已在最下级。" };
  }
  const tmp = list[idx].sort_order;
  list[idx].sort_order = list[target].sort_order;
  list[target].sort_order = tmp;
  persistSensitivityLevels(list);
  return { ok: true, message: direction === "up" ? "已上移。" : "已下移。" };
}
