/**
 * 数据字段 ↔ 密级（grade_label）绑定 — 前端模拟。
 * 对齐后端 FieldClassGrade；联调路径见规格 fields/class-grade。
 */

import { loadDataFieldCatalogEntries, DATA_FIELD_CATALOG_PERSIST_EVENT } from "./dataFieldCatalogMock.js";
import { getSensitivityLevelByLabel, SENSITIVITY_LEVEL_PERSIST_EVENT } from "./sensitivityLevelMock.js";
import { getClassGradesCache, hasClassGradesCache, setClassGradesCache } from "../stores/spaceConfigCache.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const FIELD_CLASS_GRADE_STORAGE_KEY = "dsms_mock_field_class_grade_bindings_v1";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(FIELD_CLASS_GRADE_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
export const FIELD_CLASS_GRADE_PERSIST_EVENT = "dsms-field-class-grade-persisted";

export { DATA_FIELD_CATALOG_PERSIST_EVENT, SENSITIVITY_LEVEL_PERSIST_EVENT };

function bumpListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(FIELD_CLASS_GRADE_PERSIST_EVENT));
  }
}

/** @param {any} raw */
function normalizeBinding(raw) {
  return {
    field_catalog_entry_id: String(raw?.field_catalog_entry_id || raw?.fieldCatalogEntryId || ""),
    grade_label: raw?.grade_label != null ? String(raw.grade_label).trim() : "",
    notes: String(raw?.notes || "").trim(),
    updatedAt: raw?.updatedAt || new Date().toISOString().slice(0, 10)
  };
}

export function loadFieldClassGradeBindings() {
  clearLegacySessionStorage();
  if (hasClassGradesCache()) {
    return getClassGradesCache().map(normalizeBinding);
  }
  return [];
}

function persistFieldClassGradeBindings(list, silent = false) {
  const normalized = list.map(normalizeBinding);
  setClassGradesCache(normalized);
  if (!silent) bumpListeners();
  return normalized;
}

/** @param {string} fieldCatalogEntryId */
export function getFieldClassGradeBinding(fieldCatalogEntryId) {
  const id = String(fieldCatalogEntryId || "").trim();
  return loadFieldClassGradeBindings().find((b) => b.field_catalog_entry_id === id) || null;
}

/** @param {string} gradeLabel */
export function countFieldBindingsByGradeLabel(gradeLabel) {
  const lab = String(gradeLabel || "").trim();
  return loadFieldClassGradeBindings().filter((b) => b.grade_label === lab).length;
}

export function loadFieldCatalogWithGradeBindings() {
  const bindings = new Map(
    loadFieldClassGradeBindings().map((b) => [b.field_catalog_entry_id, b])
  );
  return loadDataFieldCatalogEntries().map((entry) => {
    const b = bindings.get(entry.id);
    return {
      ...entry,
      grade_label: b?.grade_label || "",
      grade_notes: b?.notes || "",
      grade_updatedAt: b?.updatedAt || ""
    };
  });
}

/**
 * @param {string} fieldCatalogEntryId
 * @param {string | null | undefined} gradeLabel
 * @param {string} [notes]
 */
export function setFieldClassGradeBinding(fieldCatalogEntryId, gradeLabel, notes = "") {
  const id = String(fieldCatalogEntryId || "").trim();
  if (!id) return { ok: false, message: "请先选择数据字段。" };
  const lab = gradeLabel == null ? "" : String(gradeLabel).trim();
  const entries = loadDataFieldCatalogEntries();
  if (!entries.some((e) => e.id === id)) return { ok: false, message: "未找到该数据字段。" };
  if (lab && !getSensitivityLevelByLabel(lab)) {
    return { ok: false, message: `密级「${lab}」未在「密级定义」中注册，请先维护密级。` };
  }
  const list = loadFieldClassGradeBindings();
  const idx = list.findIndex((b) => b.field_catalog_entry_id === id);
  const today = new Date().toISOString().slice(0, 10);
  if (!lab) {
    if (idx < 0) return { ok: true, message: "该字段本无密级绑定。" };
    persistFieldClassGradeBindings(list.filter((b) => b.field_catalog_entry_id !== id));
    return { ok: true, message: "已清除密级绑定。" };
  }
  const row = { field_catalog_entry_id: id, grade_label: lab, notes: String(notes || "").trim(), updatedAt: today };
  if (idx >= 0) list[idx] = row;
  else list.push(row);
  persistFieldClassGradeBindings(list);
  return { ok: true, message: "已保存密级绑定。" };
}

/** 密级名称变更时同步绑定表 */
export function rebindGradeLabel(fromLabel, toLabel) {
  const from = String(fromLabel || "").trim();
  const to = String(toLabel || "").trim();
  if (!from || !to || from === to) return;
  const list = loadFieldClassGradeBindings();
  let changed = false;
  for (const b of list) {
    if (b.grade_label === from) {
      b.grade_label = to;
      b.updatedAt = new Date().toISOString().slice(0, 10);
      changed = true;
    }
  }
  if (changed) persistFieldClassGradeBindings(list);
}
