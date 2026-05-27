import { effectivePlatformRole, PLATFORM_ROLE } from "./usePortalMenuVisibility";

import { getPortalTaskCache } from "../api/portalApi.js";

import { foWorkflowProgressKey } from "../data/submissionFoWorkflowMock.js";



export const SUBMISSION_TASKS_PERSIST_EVENT = "dsms-submission-tasks-persisted";



/** @deprecated 保留导出兼容 */

export const MOCK_FO_BOUND_FUNCTION_IDS = ["field_usage", "field_request"];



/**

 * 功能 FO 侧栏「填报任务管理」红点数量（同步回退；Dashboard 优先走 API）。

 */

export function computeFoSubmissionReminderCount(me, boundFunctionIds = null) {

  if (!me || effectivePlatformRole(me) !== PLATFORM_ROLE.FUNCTION_FO) return 0;

  const tasks = getPortalTaskCache();

  if (!tasks.length) return 0;

  const bound = boundFunctionIds?.length

    ? boundFunctionIds

    : [...new Set(tasks.map((t) => t.functionId))];

  if (!bound.length) return 0;

  return tasks.filter((t) => {

    if (t.status !== "dispatched") return false;

    if (!bound.includes(t.functionId)) return false;

    if (t.foCancellationRequested) return false;

    const k = foWorkflowProgressKey(t);

    return k === "not_started" || k === "relevance_draft" || k === "lifecycle_draft";

  }).length;

}



export function bumpSubmissionTaskPersistListeners() {

  window.dispatchEvent(new CustomEvent(SUBMISSION_TASKS_PERSIST_EVENT));

}

