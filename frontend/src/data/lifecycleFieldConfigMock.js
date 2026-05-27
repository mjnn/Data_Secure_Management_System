/** 数据安全生命周期元字段 — 只读适配层；真源 `fetchLifecycleFieldConfig`。 */

import { getCatalogLabelsSorted } from "./dataFieldCatalogMock.js";
import { getLifecycleFieldsCache, setLifecycleFieldsCache } from "../stores/spaceConfigCache.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const LIFECYCLE_FIELD_CONFIG_STORAGE_KEY = "dsms_mock_lifecycle_field_config_v1";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(LIFECYCLE_FIELD_CONFIG_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
export const LIFECYCLE_FIELD_CONFIG_PERSIST_EVENT = "dsms-lifecycle-field-config-persisted";

function bumpLifecycleConfigListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(LIFECYCLE_FIELD_CONFIG_PERSIST_EVENT));
  }
}

/** 内置：数据字段（主数据条目，单选） */
export const LIFECYCLE_BUILTIN_DATA_FIELD_KEY = "data_field";
/** 内置：业务功能（填报时由本人绑定功能自动带出；多绑定时可搜索单选） */
export const LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY = "business_function";

/** @typedef {{ field_key: string; label: string; input_type: string; is_builtin: boolean; sort_order: number; help_text?: string | null; required: boolean; min_length?: number | null; max_length?: number | null; regex_pattern?: string | null; regex_error_message?: string | null; allowed_values: string[] }} LifecycleFieldConfigItem */

export function parseAllowedValuesCommaText(text) {
  return (text || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/** @param {LifecycleFieldConfigItem} item */
export function configItemToTableRow(item) {
  const allowed = Array.isArray(item.allowed_values) ? item.allowed_values : [];
  return {
    ...item,
    allowed_values: [...allowed],
    allowed_values_text: allowed.join(", ")
  };
}

/** 模拟主数据「数据字段」种子（仅当目录为空时写入目录；运行时选项以目录为准） */
export const MOCK_CATALOG_DATA_FIELD_OPTIONS = [
  "主数据字段：客户编号",
  "主数据字段：车辆 VIN",
  "主数据字段：动力总成件号",
  "主数据字段：软件版本号"
];

function catalogLabelsOrSeed() {
  const fromCat = getCatalogLabelsSorted();
  return fromCat.length ? fromCat : [...MOCK_CATALOG_DATA_FIELD_OPTIONS];
}

function builtinDataFieldRow() {
  return configItemToTableRow({
    field_key: LIFECYCLE_BUILTIN_DATA_FIELD_KEY,
    label: "数据字段",
    input_type: "single_select",
    is_builtin: true,
    sort_order: 0,
    help_text: "选项在「字段管理 — 数据字段」页维护；此处不可直接改允许值列表。",
    required: true,
    min_length: null,
    max_length: null,
    regex_pattern: null,
    regex_error_message: null,
    allowed_values: catalogLabelsOrSeed()
  });
}

function builtinBusinessFunctionRow() {
  return configItemToTableRow({
    field_key: LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY,
    label: "业务功能",
    input_type: "single_select",
    is_builtin: true,
    sort_order: 1,
    help_text:
      "填报时自动带出当前功能 FO 已绑定的业务功能；若绑定多项，提供模糊搜索 + 单选。配置表中可不维护选项文本。",
    required: true,
    min_length: null,
    max_length: null,
    regex_pattern: null,
    regex_error_message: null,
    allowed_values: []
  });
}

/**
 * 保证存在两条内置必填字段，且固定顺序在表首；其余字段顺延 sort_order。
 * @param {any[]} rows
 */
export function mergeWithBuiltinLifecycleRows(rows) {
  const list = Array.isArray(rows) ? rows.map((r) => ({ ...r })) : [];
  const byKey = new Map(list.map((r) => [r.field_key, r]));

  const dataRow = builtinDataFieldRow();
  const prevData = byKey.get(LIFECYCLE_BUILTIN_DATA_FIELD_KEY);
  if (prevData?.help_text) dataRow.help_text = prevData.help_text;

  const bizRow = builtinBusinessFunctionRow();
  const prevBiz = byKey.get(LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY);
  if (prevBiz?.help_text) bizRow.help_text = prevBiz.help_text;

  const others = list.filter(
    (r) => r.field_key !== LIFECYCLE_BUILTIN_DATA_FIELD_KEY && r.field_key !== LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY
  );
  others.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

  const merged = [dataRow, bizRow, ...others.map((r, i) => ({ ...r, sort_order: i + 2 }))];
  return merged.map((r, i) => {
    const n = normalizeStoredItem(r, i);
    n.sort_order = i;
    return configItemToTableRow(n);
  });
}

/** @param {any} raw */
function normalizeStoredItem(raw, index) {
  let allowed = Array.isArray(raw?.allowed_values) ? raw.allowed_values.map((x) => String(x)) : [];
  if (!allowed.length && raw?.allowed_values_text != null) {
    allowed = parseAllowedValuesCommaText(String(raw.allowed_values_text));
  }
  return {
    field_key: String(raw?.field_key || "").trim() || `field_${index}`,
    label: String(raw?.label || "未命名字段"),
    input_type: ["text", "textarea", "single_select", "multi_select"].includes(raw?.input_type) ? raw.input_type : "text",
    is_builtin: Boolean(raw?.is_builtin),
    sort_order: typeof raw?.sort_order === "number" ? raw.sort_order : index,
    help_text: raw?.help_text != null ? String(raw.help_text) : "",
    required: Boolean(raw?.required),
    min_length: raw?.min_length != null ? Number(raw.min_length) : null,
    max_length: raw?.max_length != null ? Number(raw.max_length) : null,
    regex_pattern: raw?.regex_pattern != null ? String(raw.regex_pattern) : null,
    regex_error_message: raw?.regex_error_message != null ? String(raw.regex_error_message) : null,
    allowed_values: allowed.filter(Boolean)
  };
}

/** @returns {ReturnType<typeof configItemToTableRow>[]} */
export function loadLifecycleFieldConfigTableRows() {
  clearLegacySessionStorage();
  const cached = getLifecycleFieldsCache();
  return mergeWithBuiltinLifecycleRows(cached?.length ? cached : []);
}

/** 供功能 FO 填报表使用的列顺序：数据字段、业务功能、其余按 sort_order */
export function getOrderedLifecycleFieldsForFoTable() {
  return loadLifecycleFieldConfigTableRows();
}

/**
 * @param {string[]} columnKeys
 * @param {Array<{ field_key: string; input_type: string }>} columnsMeta
 */
export function buildEmptyLifecycleFillRow(columnKeys, columnsMeta) {
  const metaByKey = new Map(columnsMeta.map((c) => [c.field_key, c]));
  const o = {};
  for (const k of columnKeys) {
    const t = metaByKey.get(k)?.input_type;
    o[k] = t === "multi_select" ? [] : "";
  }
  return o;
}

/** @param {ReturnType<typeof configItemToTableRow>[]} rows */
export function persistLifecycleFieldConfigFromTableRows(rows) {
  const items = tableRowsToConfigItems(rows);
  setLifecycleFieldsCache(items);
  bumpLifecycleConfigListeners();
}

/** @returns {LifecycleFieldConfigItem[]} */
export function tableRowsToConfigItems(rows) {
  return rows.map((row, i) => {
    const allowed = parseAllowedValuesCommaText(row.allowed_values_text);
    return {
      field_key: String(row.field_key || "").trim(),
      label: String(row.label || "").trim(),
      input_type: row.input_type,
      is_builtin: Boolean(row.is_builtin),
      sort_order: typeof row.sort_order === "number" ? row.sort_order : i,
      help_text: row.help_text || null,
      required: Boolean(row.required),
      min_length: row.min_length != null ? row.min_length : null,
      max_length: row.max_length != null ? row.max_length : null,
      regex_pattern: row.regex_pattern || null,
      regex_error_message: row.regex_error_message || null,
      allowed_values: allowed
    };
  });
}

export function createEmptyLifecycleFieldTableRow(sortOrder) {
  return {
    field_key: `custom_${Date.now()}`,
    label: "新字段",
    input_type: "text",
    is_builtin: false,
    sort_order: sortOrder,
    help_text: "",
    required: false,
    min_length: null,
    max_length: null,
    regex_pattern: null,
    regex_error_message: null,
    allowed_values: [],
    allowed_values_text: ""
  };
}
