/**
 * 相关性标准表达式逻辑树（问卷问题 × 答案谓词）。
 */

import {
  createEmptyRelevanceConditionFields,
  evaluateRelevanceConditionForAnswers,
  formatRelevanceConditionLabel,
  hydrateRelevanceConditionFields,
  parseLegacyPredicateId,
  parseRelevanceConditionValueKey,
  syncRelevanceConditionValueKey
} from "./relevanceConditionCatalog.js";

export const RELEVANCE_LOGIC_OPERATORS = [
  { label: "且 (AND)", value: "AND" },
  { label: "或 (OR)", value: "OR" }
];

let nextNodeId = 1;

export function newRelevanceConditionNode() {
  return {
    id: `rel_cond_${Date.now()}_${nextNodeId++}`,
    type: "condition",
    ...createEmptyRelevanceConditionFields()
  };
}

export function newRelevanceGroupNode() {
  return {
    id: `rel_grp_${Date.now()}_${nextNodeId++}`,
    type: "group",
    op: "AND",
    children: [newRelevanceConditionNode()]
  };
}

/** @param {any} raw */
export function normalizeRelevanceCondition(raw) {
  const cond = hydrateRelevanceConditionFields({
    id: String(raw?.id || newRelevanceConditionNode().id),
    type: "condition",
    valueKey: String(raw?.valueKey || ""),
    questionId: raw?.questionId,
    answerId: raw?.answerId
  });
  syncRelevanceConditionValueKey(cond);
  return cond;
}

/** @param {any} raw */
export function normalizeRelevanceGroup(raw) {
  const children = Array.isArray(raw?.children) && raw.children.length
    ? raw.children.map((c) => (c?.type === "group" ? normalizeRelevanceGroup(c) : normalizeRelevanceCondition(c)))
    : [newRelevanceConditionNode()];
  return {
    id: String(raw?.id || newRelevanceGroupNode().id),
    type: "group",
    op: raw?.op === "OR" ? "OR" : "AND",
    children
  };
}

export function walkRelevanceConditions(node, visit) {
  if (!node) return;
  if (node.type === "condition") {
    visit(node);
    return;
  }
  if (node.type === "group" && Array.isArray(node.children)) {
    for (const c of node.children) walkRelevanceConditions(c, visit);
  }
}

export function collectRelevanceConditions(root) {
  const list = [];
  walkRelevanceConditions(root, (c) => list.push(c));
  return list;
}

/**
 * @param {object} node
 * @param {Record<string, string>} answersByQuestionId
 * @param {Record<string, boolean>} [truthOverride] 条件 id → 手动覆盖
 */
export function evaluateRelevanceLogic(node, answersByQuestionId, truthOverride = {}) {
  if (!node) return false;
  if (node.type === "condition") {
    if (Object.prototype.hasOwnProperty.call(truthOverride, node.id)) {
      return Boolean(truthOverride[node.id]);
    }
    if (!node.valueKey || !parseRelevanceConditionValueKey(node.valueKey)) return false;
    return evaluateRelevanceConditionForAnswers(answersByQuestionId, node.valueKey);
  }
  if (node.type === "group") {
    const kids = (node.children || []).filter(Boolean);
    if (!kids.length) return false;
    if (node.op === "OR") {
      return kids.some((c) => evaluateRelevanceLogic(c, answersByQuestionId, truthOverride));
    }
    return kids.every((c) => evaluateRelevanceLogic(c, answersByQuestionId, truthOverride));
  }
  return false;
}

function formatNodeDisplay(node) {
  if (!node) return "";
  if (node.type === "condition") {
    return formatRelevanceConditionLabel(node.valueKey);
  }
  const kids = (node.children || []).filter(Boolean);
  if (!kids.length) return "（空）";
  const inner = kids.map((c) => formatNodeDisplay(c)).join(node.op === "OR" ? " 或 " : " 且 ");
  return kids.length > 1 ? `(${inner})` : inner;
}

export function formatRelevanceLogicDisplay(root) {
  return formatNodeDisplay(root) || "—";
}

function validateNode(root, depth = 0) {
  if (!root) return { ok: false, message: "表达式条件为空。" };
  if (depth > 12) return { ok: false, message: "分组嵌套过深。" };

  if (root.type === "condition") {
    syncRelevanceConditionValueKey(root);
    if (!String(root.valueKey || "").trim() || !parseRelevanceConditionValueKey(root.valueKey)) {
      return { ok: false, message: "请完整选择问题与答案。" };
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

export function validateRelevanceLogicRoot(root) {
  if (!collectRelevanceConditions(root).length) {
    return { ok: false, message: "请至少配置一条谓词（问题 + 答案）。" };
  }
  return validateNode(root);
}

/** @param {{ predicateId: string }} segment */
function segmentToCondition(segment) {
  const legacy = parseLegacyPredicateId(segment?.predicateId);
  if (legacy) {
    const c = newRelevanceConditionNode();
    c.questionId = legacy.questionId;
    c.answerId = legacy.answerId;
    syncRelevanceConditionValueKey(c);
    return c;
  }
  return newRelevanceConditionNode();
}

/**
 * 旧版扁平 segments + operators 迁移为逻辑树（左结合）。
 * @param {{ predicateId: string }[]} segments
 * @param {string[]} operators
 */
export function migrateLegacySegmentsToRoot(segments, operators) {
  const conds = (segments || [])
    .map((s) => segmentToCondition(s))
    .filter((c) => c.valueKey && parseRelevanceConditionValueKey(c.valueKey));
  if (!conds.length) return newRelevanceGroupNode();
  if (conds.length === 1) {
    return { ...newRelevanceGroupNode(), children: conds };
  }
  let node = conds[0];
  for (let i = 0; i < conds.length - 1; i++) {
    const op = operators?.[i] === "OR" ? "OR" : "AND";
    node = {
      id: `rel_grp_mig_${Date.now()}_${i}`,
      type: "group",
      op,
      children: [node, conds[i + 1]]
    };
  }
  return {
    id: newRelevanceGroupNode().id,
    type: "group",
    op: "AND",
    children: [node]
  };
}
