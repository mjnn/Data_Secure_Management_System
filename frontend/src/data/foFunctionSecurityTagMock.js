/**
 * 业务功能「数据安全不相关」标记 — 由已提交任务的 foRelevanceConclusion 推导。
 */
import { getPortalTaskCache } from "../api/portalApi.js";

/** @param {string} functionId */
export function isFunctionMarkedIrrelevant(functionId) {
  const fid = String(functionId || "").trim();
  if (!fid) return false;
  return getPortalTaskCache().some(
    (t) => t.functionId === fid && t.foRelevanceConclusion === "irrelevant" && t.foFillStatus === "submitted"
  );
}

/** 工作流提交后状态在任务 PATCH 中；此处保留空操作以兼容旧调用。 */
export function markFunctionDataSecurityIrrelevant(_functionId) {
  /* 状态由 submissionFoWorkflowMock + 后端任务字段承载 */
}

export function loadIrrelevantFunctionIds() {
  const set = new Set();
  for (const t of getPortalTaskCache()) {
    if (t.foRelevanceConclusion === "irrelevant" && t.functionId) {
      set.add(t.functionId);
    }
  }
  return [...set];
}
