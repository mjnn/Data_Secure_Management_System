/**
 * 相关性表达式条件 — 问卷「问题 × 答案」谓词（valueKey: qa::questionId::optionId）。
 */

import { loadRelevanceQuestionnaireQuestions } from "./relevanceQuestionnaireMock.js";

/** 展示：题目 — 选项 */
export const RELEVANCE_CONDITION_LABEL_SEPARATOR = "：";

export function createEmptyRelevanceConditionFields() {
  return {
    questionId: "",
    answerId: "",
    valueKey: ""
  };
}

/** @param {string} questionId @param {string} answerId */
export function buildRelevanceConditionValueKey(questionId, answerId) {
  const q = String(questionId || "").trim();
  const o = String(answerId || "").trim();
  if (!q || !o) return "";
  return `qa::${q}::${o}`;
}

/** @param {string} valueKey */
export function parseRelevanceConditionValueKey(valueKey) {
  const m = String(valueKey || "").match(/^qa::([^:]+)::([^:]+)$/);
  if (!m) return null;
  return { questionId: m[1], answerId: m[2] };
}

/** @param {object} cond */
export function syncRelevanceConditionValueKey(cond) {
  cond.valueKey = buildRelevanceConditionValueKey(cond.questionId, cond.answerId);
  return cond;
}

/** @param {object} raw */
export function hydrateRelevanceConditionFields(raw) {
  const cond = {
    ...createEmptyRelevanceConditionFields(),
    ...raw
  };
  const parsed = parseRelevanceConditionValueKey(cond.valueKey);
  if (parsed) {
    if (!cond.questionId) cond.questionId = parsed.questionId;
    if (!cond.answerId) cond.answerId = parsed.answerId;
  }
  if (!cond.valueKey && cond.questionId && cond.answerId) {
    syncRelevanceConditionValueKey(cond);
  }
  return cond;
}

/** @returns {{ id: string, title: string, key: string }[]} */
export function listRelevanceQuestionOptions() {
  return loadRelevanceQuestionnaireQuestions().map((q) => ({
    id: q.id,
    title: String(q.title || q.key || "").trim(),
    key: String(q.key || "").trim()
  }));
}

/** @param {string} questionId */
export function listRelevanceAnswerOptions(questionId) {
  const qid = String(questionId || "").trim();
  if (!qid) return [];
  const q = loadRelevanceQuestionnaireQuestions().find((x) => x.id === qid);
  if (!q) return [];
  return (q.options || []).map((o) => ({
    id: o.id,
    label: String(o.label || "").trim()
  }));
}

/** @param {string} valueKey */
export function formatRelevanceConditionLabel(valueKey) {
  const parsed = parseRelevanceConditionValueKey(valueKey);
  if (!parsed) return "（未配置）";
  const questions = loadRelevanceQuestionnaireQuestions();
  const q = questions.find((x) => x.id === parsed.questionId);
  const title = String(q?.title || parsed.questionId).trim();
  const opt = (q?.options || []).find((o) => o.id === parsed.answerId);
  const ans = String(opt?.label || parsed.answerId).trim();
  return `${title}${RELEVANCE_CONDITION_LABEL_SEPARATOR}${ans}`;
}

/**
 * 根据问卷作答判断是否命中条件。
 * @param {Record<string, string>} answersByQuestionId questionId → optionId
 * @param {string} valueKey
 */
export function evaluateRelevanceConditionForAnswers(answersByQuestionId, valueKey) {
  const parsed = parseRelevanceConditionValueKey(valueKey);
  if (!parsed) return false;
  return String(answersByQuestionId?.[parsed.questionId] || "") === parsed.answerId;
}

/** 旧谓词 id：questionId__optionId */
export function parseLegacyPredicateId(predicateId) {
  const s = String(predicateId || "").trim();
  const idx = s.indexOf("__");
  if (idx <= 0) return null;
  return { questionId: s.slice(0, idx), answerId: s.slice(idx + 2) };
}
