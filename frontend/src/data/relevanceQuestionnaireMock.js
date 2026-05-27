/**
 * 相关性判断问卷（题目 + 选项）— 只读适配层。
 * 真源：`fetchQuestionnaireQuestions` 写入 `spaceConfigCache`。
 */

import { getQuestionnaireCache, setQuestionnaireCache } from "../stores/spaceConfigCache.js";

/** @deprecated 仅用于迁移清理旧版 sessionStorage */
export const RELEVANCE_QUESTIONNAIRE_STORAGE_KEY = "dsms_mock_relevance_questionnaire_v1";
export const RELEVANCE_QUESTIONNAIRE_PERSIST_EVENT = "dsms-relevance-questionnaire-persisted";

let legacyStorageCleared = false;

function clearLegacySessionStorage() {
  if (legacyStorageCleared || typeof sessionStorage === "undefined") return;
  legacyStorageCleared = true;
  try {
    sessionStorage.removeItem(RELEVANCE_QUESTIONNAIRE_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** 与生命周期填报表一致，供 FoLifecycleFillTable 识别业务功能列 */
export const RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY = "business_function";

function bumpListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(RELEVANCE_QUESTIONNAIRE_PERSIST_EVENT));
  }
}

/** @param {any} raw */
function normalizeOption(raw, index) {
  return {
    id: String(raw?.id || `qo_${Date.now()}_${index}`),
    label: String(raw?.label || "").trim(),
    sort_order: typeof raw?.sort_order === "number" ? raw.sort_order : index
  };
}

/** @param {any} raw */
function normalizeQuestion(raw, index) {
  const opts = Array.isArray(raw?.options) ? raw.options.map((o, i) => normalizeOption(o, i)) : [];
  return {
    id: String(raw?.id || `qq_${index}`),
    key: String(raw?.key || `question_${index}`).trim(),
    title: String(raw?.title || "").trim(),
    sort_order: typeof raw?.sort_order === "number" ? raw.sort_order : index,
    options: opts,
    createdAt: raw?.createdAt || new Date().toISOString().slice(0, 10),
    updatedAt: raw?.updatedAt || new Date().toISOString().slice(0, 10)
  };
}

/** @returns {ReturnType<typeof normalizeQuestion>[]} */
export function loadRelevanceQuestionnaireQuestions() {
  clearLegacySessionStorage();
  const cached = getQuestionnaireCache();
  if (!cached?.length) return [];
  return cached.map((q, i) => normalizeQuestion(q, i)).sort((a, b) => a.sort_order - b.sort_order);
}

/** @param {ReturnType<typeof normalizeQuestion>[]} questions */
export function persistRelevanceQuestionnaireQuestions(questions) {
  const normalized = questions.map((q, i) => {
    const opts = (q.options || []).map((o, j) => ({
      ...normalizeOption(o, j),
      sort_order: j
    }));
    return {
      ...normalizeQuestion({ ...q, options: opts }, i),
      sort_order: i,
      options: opts,
      updatedAt: new Date().toISOString().slice(0, 10)
    };
  });
  setQuestionnaireCache(normalized);
  bumpListeners();
  return normalized;
}

let nextQId = 1;
let nextOptId = 1;

export function generateQuestionId() {
  return `qq_${Date.now()}_${nextQId++}`;
}

export function generateOptionId() {
  return `qo_${Date.now()}_${nextOptId++}`;
}

/** @param {string} title */
export function suggestQuestionKey(title) {
  const slug = String(title || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 48);
  if (slug && /^[a-z]/.test(slug)) return slug;
  return `q_${Date.now()}`;
}

/**
 * @param {{ title: string, key?: string, options: { label: string }[] }} payload
 */
export function addRelevanceQuestion(payload) {
  const title = String(payload.title || "").trim();
  if (!title) return { ok: false, message: "题目不能为空。" };
  const optionLabels = (payload.options || []).map((o) => String(o.label || "").trim()).filter(Boolean);
  if (!optionLabels.length) return { ok: false, message: "请至少配置一个选项。" };
  const list = loadRelevanceQuestionnaireQuestions();
  const key = String(payload.key || suggestQuestionKey(title)).trim();
  if (list.some((q) => q.key === key)) return { ok: false, message: "题目 Key 已存在，请修改。" };
  const day = new Date().toISOString().slice(0, 10);
  list.push({
    id: generateQuestionId(),
    key,
    title,
    sort_order: list.length,
    options: optionLabels.map((label, i) => ({ id: generateOptionId(), label, sort_order: i })),
    createdAt: day,
    updatedAt: day
  });
  persistRelevanceQuestionnaireQuestions(list);
  return { ok: true, message: "已新增题目。" };
}

/**
 * @param {string} questionId
 * @param {{ title: string, key?: string, options: { id?: string, label: string }[] }} payload
 */
export function updateRelevanceQuestion(questionId, payload) {
  const id = String(questionId || "").trim();
  if (!id) return { ok: false, message: "缺少题目 id。" };
  const title = String(payload.title || "").trim();
  if (!title) return { ok: false, message: "题目不能为空。" };
  const rawOpts = payload.options || [];
  const optionLabels = rawOpts.map((o) => String(o.label || "").trim()).filter(Boolean);
  if (!optionLabels.length) return { ok: false, message: "请至少保留一个选项。" };
  const list = loadRelevanceQuestionnaireQuestions();
  const idx = list.findIndex((q) => q.id === id);
  if (idx < 0) return { ok: false, message: "未找到题目。" };
  const key = String(payload.key || list[idx].key).trim();
  if (list.some((q, i) => i !== idx && q.key === key)) {
    return { ok: false, message: "题目 Key 已存在，请修改。" };
  }
  list[idx] = {
    ...list[idx],
    key,
    title,
    options: optionLabels.map((label, i) => ({
      id: rawOpts[i]?.id || generateOptionId(),
      label,
      sort_order: i
    })),
    updatedAt: new Date().toISOString().slice(0, 10)
  };
  persistRelevanceQuestionnaireQuestions(list);
  return { ok: true, message: "已保存题目。" };
}

/** @param {string} questionId */
export function removeRelevanceQuestion(questionId) {
  const id = String(questionId || "").trim();
  if (!id) return { ok: false, message: "缺少题目 id。" };
  const list = loadRelevanceQuestionnaireQuestions();
  const next = list.filter((q) => q.id !== id);
  if (next.length === list.length) return { ok: false, message: "未找到题目。" };
  persistRelevanceQuestionnaireQuestions(next);
  return { ok: true, message: "已删除题目。" };
}

/**
 * 功能 FO 填报预览列：首列业务功能，其后每道问卷题为单选列。
 * @param {ReturnType<typeof normalizeQuestion>[]} questions
 */
export function buildRelevanceQuestionnairePreviewColumns(questions) {
  const qs = Array.isArray(questions) ? [...questions].sort((a, b) => a.sort_order - b.sort_order) : [];
  const cols = [
    {
      field_key: RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY,
      label: "业务功能",
      input_type: "single_select",
      required: true,
      help_text: "填报时自动带出当前功能 FO 已绑定的业务功能；若绑定多项，提供模糊搜索 + 单选。",
      max_length: null,
      allowed_values: []
    }
  ];
  for (const q of qs) {
    const allowed = (q.options || []).map((o) => String(o.label || "").trim()).filter(Boolean);
    cols.push({
      field_key: String(q.key || "").trim(),
      label: String(q.title || q.key || "未命名题目"),
      input_type: "single_select",
      required: true,
      help_text: "",
      max_length: null,
      allowed_values: allowed
    });
  }
  return cols;
}

/**
 * 将 FO 填报行（列 key 为题目 key、值为选项文案）转为 questionId → optionId。
 * @param {Record<string, unknown>} row
 */
export function buildAnswersByQuestionIdFromFillRow(row) {
  const questions = loadRelevanceQuestionnaireQuestions();
  /** @type {Record<string, string>} */
  const answers = {};
  for (const q of questions) {
    const qKey = String(q.key || "").trim();
    if (!qKey) continue;
    const label = String(row[qKey] ?? "").trim();
    if (!label) continue;
    const opt = (q.options || []).find((o) => String(o.label || "").trim() === label);
    if (opt) answers[q.id] = opt.id;
  }
  return answers;
}

/** @param {Record<string, unknown>} row */
export function validateRelevanceFillRow(row) {
  const questions = loadRelevanceQuestionnaireQuestions();
  if (!questions.length) {
    return { ok: false, message: "请先在「相关性问卷」中配置题目。" };
  }
  const bf = String(row[RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY] ?? "").trim();
  if (!bf) return { ok: false, message: "请选择业务功能。" };
  for (const q of questions) {
    const qKey = String(q.key || "").trim();
    const val = String(row[qKey] ?? "").trim();
    if (!val) {
      return { ok: false, message: `请作答：${String(q.title || qKey).trim()}` };
    }
  }
  return { ok: true, message: "" };
}
