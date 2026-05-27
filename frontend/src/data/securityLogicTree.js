/**
 * 安全要求触发条件逻辑树（仅密级 / 分类 / 生命周期维度，求值时传入数据字段 id）。
 */

import {
  createEmptyConditionFields,
  evaluateConditionForField,
  formatSecurityConditionLabel,
  hydrateConditionFields,
  parseConditionValueKey,
  syncConditionValueKey
} from "./securityConditionCatalog.js";

export const SECURITY_LOGIC_OPERATORS = [
  { label: "且 (AND)", value: "AND" },
  { label: "或 (OR)", value: "OR" }
];

let nextNodeId = 1;

export function newTriggerConditionNode() {
  return {
    id: `sec_cond_${Date.now()}_${nextNodeId++}`,
    type: "condition",
    ...createEmptyConditionFields()
  };
}

export function newTriggerGroupNode() {
  return {
    id: `sec_grp_${Date.now()}_${nextNodeId++}`,
    type: "group",
    op: "AND",
    children: [newTriggerConditionNode()]
  };
}

/** @param {any} raw */
export function normalizeCondition(raw) {
  const cond = hydrateConditionFields({
    id: String(raw?.id || newTriggerConditionNode().id),
    type: "condition",
    valueKey: String(raw?.valueKey || ""),
    attributeKind: raw?.attributeKind,
    gradeValue: raw?.gradeValue,
    taxonomyPathStored: raw?.taxonomyPathStored,
    lifecycleFieldKey: raw?.lifecycleFieldKey,
    lifecycleValue: raw?.lifecycleValue
  });
  syncConditionValueKey(cond);
  return cond;
}

/** @param {any} raw */
export function normalizeGroup(raw) {
  const children = Array.isArray(raw?.children) && raw.children.length
    ? raw.children.map((c) => (c?.type === "group" ? normalizeGroup(c) : normalizeCondition(c)))
    : [newTriggerConditionNode()];
  return {
    id: String(raw?.id || newTriggerGroupNode().id),
    type: "group",
    op: raw?.op === "OR" ? "OR" : "AND",
    children
  };
}

export function walkConditions(node, visit) {
  if (!node) return;
  if (node.type === "condition") {
    visit(node);
    return;
  }
  if (node.type === "group" && Array.isArray(node.children)) {
    for (const c of node.children) walkConditions(c, visit);
  }
}

export function collectConditions(root) {
  const list = [];
  walkConditions(root, (c) => list.push(c));
  return list;
}

/**
 * @param {object} node
 * @param {string} fieldCatalogEntryId 被求值的数据字段
 * @param {Record<string, boolean>} [truthOverride] 条件 id → 手动覆盖
 */
export function evaluateTriggerLogic(node, fieldCatalogEntryId, truthOverride = {}) {
  if (!node) return false;
  if (node.type === "condition") {
    if (Object.prototype.hasOwnProperty.call(truthOverride, node.id)) {
      return Boolean(truthOverride[node.id]);
    }
    if (!node.valueKey || !parseConditionValueKey(node.valueKey)) return false;
    return evaluateConditionForField(fieldCatalogEntryId, node.valueKey);
  }
  if (node.type === "group") {
    const kids = (node.children || []).filter(Boolean);
    if (!kids.length) return false;
    if (node.op === "OR") {
      return kids.some((c) => evaluateTriggerLogic(c, fieldCatalogEntryId, truthOverride));
    }
    return kids.every((c) => evaluateTriggerLogic(c, fieldCatalogEntryId, truthOverride));
  }
  return false;
}

function formatNodeDisplay(node) {
  if (!node) return "";
  if (node.type === "condition") {
    return formatSecurityConditionLabel(node.valueKey);
  }
  const kids = (node.children || []).filter(Boolean);
  if (!kids.length) return "（空）";
  const inner = kids.map((c) => formatNodeDisplay(c)).join(node.op === "OR" ? " 或 " : " 且 ");
  return kids.length > 1 ? `(${inner})` : inner;
}

export function formatTriggerLogicDisplay(root) {
  return formatNodeDisplay(root) || "—";
}

function validateNode(root, depth = 0) {
  if (!root) return { ok: false, message: "触发条件为空。" };
  if (depth > 12) return { ok: false, message: "分组嵌套过深。" };

  if (root.type === "condition") {
    syncConditionValueKey(root);
    if (!String(root.valueKey || "").trim() || !parseConditionValueKey(root.valueKey)) {
      return { ok: false, message: "请完整填写密级、分类或生命周期字段条件。" };
    }
    return { ok: true, message: "" };
  }

  if (root.type === "group") {
    const kids = root.children || [];
    if (!kids.length) return { ok: false, message: "分组内至少一条条件。" };
    for (const c of kids) {
      const r = validateNode(c, depth + 1);
      if (!r.ok) return r;
    }
    return { ok: true, message: "" };
  }

  return { ok: false, message: "条件结构无效。" };
}

export function validateTriggerRoot(root) {
  if (!collectConditions(root).length) {
    return { ok: false, message: "请至少配置一条触发条件。" };
  }
  return validateNode(root);
}
