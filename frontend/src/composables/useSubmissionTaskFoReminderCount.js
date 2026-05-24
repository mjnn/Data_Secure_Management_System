import { effectivePlatformRole, PLATFORM_ROLE } from "./usePortalMenuVisibility";

import { SUBMISSION_TASKS_STORAGE_KEY } from "../data/submissionTasksMock";

export const SUBMISSION_TASKS_PERSIST_EVENT = "dsms-submission-tasks-persisted";

/** 模拟：当前登录用户作为功能 FO 时负责的业务功能 id */
export const MOCK_FO_BOUND_FUNCTION_IDS = ["f_usage", "f_req"];

/**
 * 功能 FO 侧栏「填报任务管理」红点数量：已下发至本人绑定功能、且仍处于待办（未填报或草稿）的任务数。
 * 已提交不计入；取消申请中仍计为待办（可后续按产品再调）。
 */
export function computeFoSubmissionReminderCount(me) {
  if (!me || effectivePlatformRole(me) !== PLATFORM_ROLE.FUNCTION_FO) return 0;
  let tasks = [];
  try {
    const raw = sessionStorage.getItem(SUBMISSION_TASKS_STORAGE_KEY);
    if (raw) tasks = JSON.parse(raw);
  } catch (_e) {
    /* ignore */
  }
  if (!Array.isArray(tasks)) return 0;
  return tasks.filter((t) => {
    if (t.status !== "dispatched") return false;
    if (!MOCK_FO_BOUND_FUNCTION_IDS.includes(t.functionId)) return false;
    if (t.foCancellationRequested) return false;
    const fs = t.foFillStatus || "not_started";
    return fs === "not_started" || fs === "draft";
  }).length;
}

export function bumpSubmissionTaskPersistListeners() {
  window.dispatchEvent(new CustomEvent(SUBMISSION_TASKS_PERSIST_EVENT));
}
