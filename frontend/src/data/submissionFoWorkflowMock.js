/**
 * 功能 FO 填报任务工作流：相关性 →（不相关结束 | 生命周期 → 规则识别 → 结束）。
 */

import {
  buildAnswersByQuestionIdFromFillRow,
  buildRelevanceQuestionnairePreviewColumns,
  loadRelevanceQuestionnaireQuestions,
  RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY,
  validateRelevanceFillRow
} from "./relevanceQuestionnaireMock.js";
import { resolveConclusionFromExpression, loadRelevanceExpression } from "./relevanceExpressionMock.js";
import { markFunctionDataSecurityIrrelevant } from "./foFunctionSecurityTagMock.js";
import {
  evaluateGovernanceForLifecycleRows,
  persistFieldLifecycleValuesFromFillRows
} from "./foSubmissionGovernanceMock.js";
import { syncTaskToPortal } from "../api/portalTaskSync.js";
import { submissionFunctionName } from "./submissionTasksMock.js";
import { getOrderedLifecycleFieldsForFoTable, LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY } from "./lifecycleFieldConfigMock.js";

export const FO_WORKFLOW_STEP_RELEVANCE = "relevance";
export const FO_WORKFLOW_STEP_LIFECYCLE = "lifecycle";
export const FO_WORKFLOW_STEP_DONE = "done";

export const FO_RELEVANCE_RELEVANT = "relevant";
export const FO_RELEVANCE_IRRELEVANT = "irrelevant";

/** @param {object} task */
export function normalizeFoWorkflowFields(task) {
  if (task.foWorkflowStep == null) task.foWorkflowStep = null;
  if (task.foRelevanceConclusion == null) task.foRelevanceConclusion = null;
  if (task.foRelevanceFillRow == null) task.foRelevanceFillRow = null;
  if (task.foGovernanceResult == null) task.foGovernanceResult = null;
  return task;
}

/** @param {object} task */
export function foWorkflowProgressKey(task) {
  if (task.foCancelApprovalPending) return "cancel_pending";
  if (task.foFillStatus === "cancelled" || (task.foCancellationRequested && !task.foCancelApprovalPending)) {
    return "cancelled";
  }
  if (task.foCancellationRequested) return "cancel_pending";
  if (task.foFillStatus === "submitted") {
    if (task.foRelevanceConclusion === FO_RELEVANCE_IRRELEVANT) return "completed_irrelevant";
    return "submitted";
  }
  if (task.foFillStatus === "draft") {
    if (task.foWorkflowStep === FO_WORKFLOW_STEP_LIFECYCLE) return "lifecycle_draft";
    return "relevance_draft";
  }
  return "not_started";
}

export function foWorkflowProgressLabel(task) {
  const k = foWorkflowProgressKey(task);
  const map = {
    not_started: "未填报",
    relevance_draft: "相关性填报中",
    lifecycle_draft: "生命周期填报中",
    submitted: "已提交",
    completed_irrelevant: "已结束（不相关）",
    cancel_pending: "取消申请中",
    cancelled: "已取消"
  };
  return map[k] || "未填报";
}

export function foWorkflowProgressTagType(task) {
  const k = foWorkflowProgressKey(task);
  if (k === "submitted") return "success";
  if (k === "completed_irrelevant") return "info";
  if (k === "lifecycle_draft" || k === "relevance_draft") return "warning";
  if (k === "cancel_pending") return "warning";
  return "info";
}

/** @param {string} functionId */
export function buildRelevanceColumnsForTaskFunction(functionId) {
  const questions = loadRelevanceQuestionnaireQuestions();
  return buildRelevanceQuestionnairePreviewColumns(questions);
}

/**
 * @param {string} functionId
 * @param {Record<string, unknown>} [existing]
 */
export function buildEmptyRelevanceRowForTask(functionId, existing = null) {
  const cols = buildRelevanceColumnsForTaskFunction(functionId);
  const row = { ...(existing || {}) };
  for (const c of cols) {
    if (row[c.field_key] == null) row[c.field_key] = "";
  }
  row[RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY] = functionId;
  return row;
}

/** @param {Record<string, unknown>} row */
export function evaluateRelevanceForFillRow(row) {
  const check = validateRelevanceFillRow(row);
  if (!check.ok) return { ok: false, message: check.message, conclusion: null };
  const expr = loadRelevanceExpression();
  const answers = buildAnswersByQuestionIdFromFillRow(row);
  const res = resolveConclusionFromExpression(expr, {}, answers);
  const code = res.conclusionCode === "relevant" ? FO_RELEVANCE_RELEVANT : FO_RELEVANCE_IRRELEVANT;
  return {
    ok: true,
    message: "",
    conclusion: {
      code,
      text: res.conclusionText,
      satisfied: res.satisfied,
      expressionText: res.expressionText
    }
  };
}

function buildRelevanceSnapshot(row, conclusion, submittedAt) {
  const questions = loadRelevanceQuestionnaireQuestions();
  const fields = questions.map((q) => {
    const key = String(q.key || "").trim();
    const val = String(row[key] ?? "").trim() || "—";
    return { label: q.title, value: val };
  });
  return {
    versionKey: "relevance-questionnaire@v1",
    submittedAt,
    sections: [
      {
        heading: "相关性判定",
        fields: [
          { label: "业务功能", value: submissionFunctionName(row[RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY]) },
          { label: "判定结论", value: conclusion.text },
          { label: "表达式", value: conclusion.expressionText || "—" },
          ...fields
        ]
      }
    ]
  };
}

function buildGovernanceSnapshotSections(governance) {
  const fields = [];
  for (const f of governance.fields || []) {
    fields.push({
      label: f.fieldLabel,
      value: `密级 ${f.gradeLabel} · 分类 ${f.taxPath}`
    });
    if (f.triggeredRules?.length) {
      for (const tr of f.triggeredRules) {
        fields.push({
          label: `安全要求 · ${tr.ruleName}`,
          value: tr.actionPreview
        });
      }
    } else {
      fields.push({ label: `安全要求 · ${f.fieldLabel}`, value: "未命中已配置规则" });
    }
  }
  return [
    { heading: "规则识别摘要", fields: [{ label: "说明", value: governance.summaryMessage }] },
    { heading: "分类分级与安全要求（按数据字段）", fields }
  ];
}

/**
 * @param {object} task
 * @param {Record<string, unknown>} relevanceRow
 * @param {{ code: string, text: string, expressionText?: string }} conclusion
 */
export function completeTaskAsIrrelevant(task, relevanceRow, conclusion) {
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  const fid = String(relevanceRow[RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY] || task.functionId).trim();
  markFunctionDataSecurityIrrelevant(fid);
  task.foRelevanceFillRow = { ...relevanceRow };
  task.foRelevanceConclusion = FO_RELEVANCE_IRRELEVANT;
  task.foWorkflowStep = FO_WORKFLOW_STEP_DONE;
  task.foFillStatus = "submitted";
  task.foFillContentSummary = `相关性判定：${conclusion.text}；该业务功能已标记为「数据安全不相关」，填报任务结束。`;
  task.foFillFormSnapshot = buildRelevanceSnapshot(relevanceRow, conclusion, now);
  task.foFillLifecycleRows = null;
  task.foGovernanceResult = null;
  syncTaskToPortal(task);
  return task;
}

/**
 * @param {object} task
 * @param {Record<string, unknown>} relevanceRow
 * @param {{ code: string, text: string }} conclusion
 */
export function saveTaskRelevanceDraft(task, relevanceRow, conclusion) {
  task.foFillStatus = "draft";
  task.foWorkflowStep = FO_WORKFLOW_STEP_RELEVANCE;
  task.foRelevanceFillRow = { ...relevanceRow };
  task.foRelevanceConclusion = conclusion?.code || null;
  task.foFillContentSummary = conclusion
    ? `相关性草稿：${conclusion.text}`
    : "相关性判定草稿（未提交）";
  syncTaskToPortal(task);
  return task;
}

/** @param {object} task @param {Record<string, unknown>} relevanceRow @param {{ code: string, text: string }} conclusion */
export function advanceTaskToLifecycle(task, relevanceRow, conclusion) {
  task.foFillStatus = "draft";
  task.foWorkflowStep = FO_WORKFLOW_STEP_LIFECYCLE;
  task.foRelevanceFillRow = { ...relevanceRow };
  task.foRelevanceConclusion = FO_RELEVANCE_RELEVANT;
  task.foFillContentSummary = `相关性判定：${conclusion.text}；请继续完成生命周期字段填报。`;
  if (!Array.isArray(task.foFillLifecycleRows) || !task.foFillLifecycleRows.length) {
    const cols = getOrderedLifecycleFieldsForFoTable();
    const keys = cols.map((c) => c.field_key);
    const empty = {};
    for (const k of keys) empty[k] = "";
    empty[LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY] = task.functionId;
    task.foFillLifecycleRows = [empty];
  }
  syncTaskToPortal(task);
  return task;
}

/** @param {object} task @param {Record<string, unknown>[]} lifecycleRows */
export function saveTaskLifecycleDraft(task, lifecycleRows) {
  task.foFillStatus = "draft";
  task.foWorkflowStep = FO_WORKFLOW_STEP_LIFECYCLE;
  task.foFillLifecycleRows = JSON.parse(JSON.stringify(lifecycleRows));
  task.foFillContentSummary =
    task.foRelevanceConclusion === FO_RELEVANCE_RELEVANT
      ? "相关性已判定为相关；生命周期明细草稿已保存。"
      : task.foFillContentSummary;
  syncTaskToPortal(task);
  return task;
}

/**
 * @param {object} task
 * @param {Record<string, unknown>[]} lifecycleRows
 * @param {object} lifecycleFormSnapshot from buildLifecycleFormSnapshot in page
 */
export async function completeTaskAsRelevantSubmitted(task, lifecycleRows, lifecycleFormSnapshot) {
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  persistFieldLifecycleValuesFromFillRows(lifecycleRows);
  const governance = await evaluateGovernanceForLifecycleRows(lifecycleRows);
  task.foFillLifecycleRows = JSON.parse(JSON.stringify(lifecycleRows));
  task.foWorkflowStep = FO_WORKFLOW_STEP_DONE;
  task.foFillStatus = "submitted";
  task.foRelevanceConclusion = FO_RELEVANCE_RELEVANT;
  task.foGovernanceResult = governance;
  task.foFillContentSummary = governance.summaryMessage;

  const relSnap = task.foRelevanceFillRow
    ? buildRelevanceSnapshot(task.foRelevanceFillRow, {
        text: "相关",
        expressionText: ""
      }, now)
    : null;

  task.foFillFormSnapshot = {
    versionKey: "fo-submission@v1",
    submittedAt: now,
    formTable: lifecycleFormSnapshot?.formTable,
    sections: [
      ...(relSnap?.sections || []),
      ...(lifecycleFormSnapshot?.sections || []),
      ...buildGovernanceSnapshotSections(governance)
    ]
  };
  syncTaskToPortal(task);
  return { task, governance };
}
