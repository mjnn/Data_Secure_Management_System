/**
 * 安全要求触发条件维度 — 仅密级、分类、其他生命周期元字段（不含数据字段选择）。
 * 分类/密级绑定在「数据分类标准」「密级绑定」中维护；本页对某字段求值时读取其结果。
 */

import { loadFieldCatalogWithGradeBindings } from "./fieldClassGradeBindingMock.js";
import { loadFieldCatalogWithTaxonomy } from "./fieldTaxonomyClassificationMock.js";
import {
  LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY,
  LIFECYCLE_BUILTIN_DATA_FIELD_KEY,
  loadLifecycleFieldConfigTableRows
} from "./lifecycleFieldConfigMock.js";
import { listSensitivityLevelLabels } from "./sensitivityLevelMock.js";
import {
  buildTaxonomyPathStoredFromLeafCode,
  formatTaxonomyPathDashNamesFromStoredPath
} from "./taxonomyNodeMock.js";

export const VALUE_KEY_SEP = "::";

export const SECURITY_VALUE_GROUP_GRADE = "密级";
export const SECURITY_VALUE_GROUP_TAXONOMY = "分类";
export const SECURITY_VALUE_GROUP_LIFECYCLE = "其他生命周期字段";

export const CONDITION_ATTR_GRADE = "grade";
export const CONDITION_ATTR_TAXONOMY = "taxonomy";
export const CONDITION_ATTR_LIFECYCLE = "lifecycle";

export const CONDITION_ATTR_OPTIONS = [
  { value: CONDITION_ATTR_GRADE, label: "密级" },
  { value: CONDITION_ATTR_TAXONOMY, label: "分类" },
  { value: CONDITION_ATTR_LIFECYCLE, label: "生命周期字段" }
];

/** @typedef {'taxonomy' | 'grade' | 'lifecycle'} SecurityConditionCategory */

export function buildConditionValueKey(category, value, lifecycleFieldKey = "") {
  const v = String(value || "").trim();
  if (category === "lifecycle") {
    return `lifecycle${VALUE_KEY_SEP}${String(lifecycleFieldKey || "").trim()}${VALUE_KEY_SEP}${v}`;
  }
  if (category === "grade") return `grade${VALUE_KEY_SEP}${v}`;
  return `taxonomy${VALUE_KEY_SEP}${v}`;
}

export function parseConditionValueKey(valueKey) {
  const raw = String(valueKey || "").trim();
  if (!raw) return null;
  const parts = raw.split(VALUE_KEY_SEP);
  if (parts[0] === "taxonomy" && parts[1]) {
    return { category: "taxonomy", lifecycleFieldKey: "", value: parts.slice(1).join(VALUE_KEY_SEP) };
  }
  if (parts[0] === "grade" && parts[1]) {
    return { category: "grade", lifecycleFieldKey: "", value: parts[1] };
  }
  if (parts[0] === "lifecycle" && parts[1] && parts.length >= 3) {
    return { category: "lifecycle", lifecycleFieldKey: parts[1], value: parts.slice(2).join(VALUE_KEY_SEP) };
  }
  return null;
}

export function listGradeOptions() {
  return listSensitivityLevelLabels();
}

export { buildTaxonomyTreeSelectData } from "./taxonomyNodeMock.js";

/** 生命周期元字段（非内置） */
export function listLifecycleMetaFields() {
  return loadLifecycleFieldConfigTableRows()
    .filter(
      (r) =>
        r.field_key !== LIFECYCLE_BUILTIN_DATA_FIELD_KEY &&
        r.field_key !== LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY
    )
    .map((r) => ({
      field_key: r.field_key,
      label: String(r.label || r.field_key || "").trim(),
      allowed_values: Array.isArray(r.allowed_values) ? r.allowed_values.filter(Boolean) : []
    }))
    .filter((r) => r.allowed_values.length > 0);
}

/** @param {string} lifecycleFieldKey */
export function listLifecycleValuesForMetaField(lifecycleFieldKey) {
  const key = String(lifecycleFieldKey || "").trim();
  const col = listLifecycleMetaFields().find((r) => r.field_key === key);
  return col ? col.allowed_values.map((v) => String(v).trim()).filter(Boolean) : [];
}

/** 将 UI 字段写入 valueKey */
export function syncConditionValueKey(cond) {
  if (!cond) return "";
  const kind = cond.attributeKind || CONDITION_ATTR_GRADE;
  if (kind === CONDITION_ATTR_GRADE) {
    cond.valueKey = buildConditionValueKey("grade", cond.gradeValue || "");
  } else if (kind === CONDITION_ATTR_TAXONOMY) {
    cond.valueKey = buildConditionValueKey("taxonomy", cond.taxonomyPathStored || "");
  } else if (kind === CONDITION_ATTR_LIFECYCLE) {
    cond.valueKey = buildConditionValueKey(
      "lifecycle",
      cond.lifecycleValue || "",
      cond.lifecycleFieldKey || ""
    );
  } else {
    cond.valueKey = "";
  }
  return cond.valueKey;
}

/** 从 valueKey 还原 UI 字段 */
export function hydrateConditionFields(cond) {
  if (!cond) return cond;
  const parsed = parseConditionValueKey(cond.valueKey);
  if (!parsed) {
    cond.attributeKind = cond.attributeKind || CONDITION_ATTR_GRADE;
    cond.gradeValue = cond.gradeValue || "";
    cond.taxonomyPathStored = cond.taxonomyPathStored || "";
    cond.lifecycleFieldKey = cond.lifecycleFieldKey || "";
    cond.lifecycleValue = cond.lifecycleValue || "";
    return cond;
  }
  cond.attributeKind = parsed.category;
  if (parsed.category === "grade") {
    cond.gradeValue = parsed.value;
    cond.taxonomyPathStored = "";
    cond.lifecycleFieldKey = "";
    cond.lifecycleValue = "";
  } else if (parsed.category === "taxonomy") {
    cond.taxonomyPathStored = parsed.value;
    cond.gradeValue = "";
    cond.lifecycleFieldKey = "";
    cond.lifecycleValue = "";
  } else {
    cond.lifecycleFieldKey = parsed.lifecycleFieldKey;
    cond.lifecycleValue = parsed.value;
    cond.gradeValue = "";
    cond.taxonomyPathStored = "";
  }
  return cond;
}

export function createEmptyConditionFields() {
  return hydrateConditionFields({
    attributeKind: CONDITION_ATTR_GRADE,
    gradeValue: "",
    taxonomyPathStored: "",
    lifecycleFieldKey: "",
    lifecycleValue: "",
    valueKey: ""
  });
}

/** @param {string} valueKey */
export function formatSecurityConditionLabel(valueKey) {
  const parsed = parseConditionValueKey(valueKey);
  if (!parsed) return "（未配置条件）";

  if (parsed.category === "taxonomy") {
    const pathLabel = formatTaxonomyPathDashNamesFromStoredPath(parsed.value);
    return `分类：${pathLabel}`;
  }
  if (parsed.category === "grade") {
    return `密级：${parsed.value}`;
  }
  const col = loadLifecycleFieldConfigTableRows().find((r) => r.field_key === parsed.lifecycleFieldKey);
  const colLabel = col?.label || parsed.lifecycleFieldKey;
  return `${colLabel}：${parsed.value}`;
}

/** @param {string} _fieldCatalogEntryId */
function readLifecycleValuesForField(_fieldCatalogEntryId) {
  return {};
}

/**
 * 对指定数据字段，按其已绑定的密级/分类及生命周期取值，判断单条条件是否成立。
 * @param {string} fieldCatalogEntryId
 * @param {string} valueKey
 */
export function evaluateConditionForField(fieldCatalogEntryId, valueKey) {
  const parsed = parseConditionValueKey(valueKey);
  const id = String(fieldCatalogEntryId || "").trim();
  if (!parsed || !id) return false;

  if (parsed.category === "taxonomy") {
    const taxRow = loadFieldCatalogWithTaxonomy().find((f) => f.id === id);
    const leaf = String(taxRow?.taxonomy_code || "").trim();
    if (!leaf) return false;
    return buildTaxonomyPathStoredFromLeafCode(leaf) === parsed.value;
  }

  if (parsed.category === "grade") {
    const gradeRow = loadFieldCatalogWithGradeBindings().find((f) => f.id === id);
    return String(gradeRow?.grade_label || "").trim() === parsed.value;
  }

  if (parsed.category === "lifecycle") {
    const vals = readLifecycleValuesForField(id);
    const actual = vals[parsed.lifecycleFieldKey];
    if (actual == null) return false;
    if (Array.isArray(actual)) return actual.map(String).includes(parsed.value);
    return String(actual).trim() === parsed.value;
  }

  return false;
}

/** 求值时展示字段已具备的密级/分类（便于试算对照） */
export function describeFieldGovernanceSnapshot(fieldCatalogEntryId) {
  const id = String(fieldCatalogEntryId || "").trim();
  const tax = loadFieldCatalogWithTaxonomy().find((f) => f.id === id);
  const grade = loadFieldCatalogWithGradeBindings().find((f) => f.id === id);
  const taxPath = tax?.taxonomy_code
    ? formatTaxonomyPathDashNamesFromStoredPath(buildTaxonomyPathStoredFromLeafCode(tax.taxonomy_code))
    : "未分类";
  const gradeLabel = grade?.grade_label || "未绑定密级";
  return { gradeLabel, taxPath };
}
