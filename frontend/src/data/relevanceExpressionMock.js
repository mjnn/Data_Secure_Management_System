/**
 * 相关性标准表达式 — 逻辑树连接「问题 × 答案」谓词，映射相关/不相关结论。
 */

import {
  buildAnswersByQuestionIdFromFillRow,
  loadRelevanceQuestionnaireQuestions,
  validateRelevanceFillRow
} from "./relevanceQuestionnaireMock.js";
import { getRelevanceExpressionCache, setRelevanceExpressionCache } from "../stores/spaceConfigCache.js";
import {
  evaluateRelevanceLogic,
  formatRelevanceLogicDisplay,
  newRelevanceGroupNode,
  normalizeRelevanceGroup,
  validateRelevanceLogicRoot
} from "./relevanceLogicTree.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const RELEVANCE_EXPRESSION_STORAGE_KEY = "dsms_mock_relevance_expression_v2";
export const RELEVANCE_EXPRESSION_PERSIST_EVENT = "dsms-relevance-expression-persisted";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(RELEVANCE_EXPRESSION_STORAGE_KEY);
    sessionStorage.removeItem("dsms_mock_relevance_expression_v1");
  } catch {
    /* ignore */
  }
}

export const RELEVANCE_CONCLUSION_OPTIONS = [
  { label: "相关", value: "relevant" },
  { label: "不相关", value: "irrelevant" }
];

function bumpExpressionListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(RELEVANCE_EXPRESSION_PERSIST_EVENT));
  }
}

function defaultExpression() {
  return {
    logic_root: newRelevanceGroupNode(),
    conclusionWhenTrue: "relevant",
    conclusionWhenFalse: "irrelevant",
    updatedAt: new Date().toISOString().slice(0, 10)
  };
}

export function loadRelevanceExpression() {
  clearLegacySessionStorage();
  const cached = getRelevanceExpressionCache();
  if (cached) return cached;
  return defaultExpression();
}

export function persistRelevanceExpression(expr) {
  const payload = {
    logic_root: normalizeRelevanceGroup(expr.logic_root || newRelevanceGroupNode()),
    conclusionWhenTrue: expr.conclusionWhenTrue === "irrelevant" ? "irrelevant" : "relevant",
    conclusionWhenFalse: expr.conclusionWhenFalse === "relevant" ? "relevant" : "irrelevant",
    updatedAt: new Date().toISOString().slice(0, 10)
  };
  setRelevanceExpressionCache(payload);
  bumpExpressionListeners();
  return payload;
}

export function formatExpressionDisplay(expr) {
  return formatRelevanceLogicDisplay(expr?.logic_root);
}

export function evaluateRelevanceExpression(expr, truthByConditionId, answersByQuestionId = {}) {
  return evaluateRelevanceLogic(expr?.logic_root, answersByQuestionId, truthByConditionId);
}

export function conclusionLabel(value) {
  return value === "relevant" ? "相关" : "不相关";
}

export function resolveConclusionFromExpression(expr, truthByConditionId, answersByQuestionId = {}) {
  const satisfied = evaluateRelevanceExpression(expr, truthByConditionId, answersByQuestionId);
  const code = satisfied ? expr.conclusionWhenTrue : expr.conclusionWhenFalse;
  return {
    satisfied,
    conclusionCode: code,
    conclusionText: conclusionLabel(code),
    expressionText: formatExpressionDisplay(expr)
  };
}

export function validateExpressionPayload(expr) {
  return validateRelevanceLogicRoot(expr?.logic_root);
}

export function hasRelevanceQuestionnaireForExpression() {
  return loadRelevanceQuestionnaireQuestions().length > 0;
}

/** @param {object} expr @param {Record<string, unknown>} fillRow */
export function resolveConclusionFromFillRow(expr, fillRow) {
  const fillCheck = validateRelevanceFillRow(fillRow);
  if (!fillCheck.ok) return { ok: false, ...fillCheck, result: null };

  const exprCheck = validateExpressionPayload(expr);
  if (!exprCheck.ok) return { ok: false, ...exprCheck, result: null };

  const answersByQuestionId = buildAnswersByQuestionIdFromFillRow(fillRow);
  const result = resolveConclusionFromExpression(expr, {}, answersByQuestionId);
  return { ok: true, message: "", result };
}
