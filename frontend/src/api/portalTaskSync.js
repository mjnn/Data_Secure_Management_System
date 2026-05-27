/** 将任务对象同步到后端（工作流 mock 落库）。 */

import { patchSubmissionTask } from "./portalApi.js";

import { normalizeSubmissionTask } from "../data/submissionTasksMock.js";



let ctx = { tenantId: null, spaceId: null };



export function setPortalSyncContext(tenantId, spaceId) {

  ctx = { tenantId, spaceId };

}



function taskPatchPayload(task) {

  return {

    foFillStatus: task.foFillStatus,

    foFillContentSummary: task.foFillContentSummary,

    foFillFormSnapshot: task.foFillFormSnapshot,

    foFillLifecycleRows: task.foFillLifecycleRows,

    foCancellationRequested: task.foCancellationRequested,

    foCancellationReason: task.foCancellationReason,

    foCancelApprovalPending: task.foCancelApprovalPending,

    foWorkflowStep: task.foWorkflowStep,

    foRelevanceConclusion: task.foRelevanceConclusion,

    foRelevanceFillRow: task.foRelevanceFillRow,

    foGovernanceResult: task.foGovernanceResult,

    auditStatus: task.auditStatus,

    auditComment: task.auditComment,

    auditedAt: task.auditedAt

  };

}



/** PATCH 任务；`foFillStatus=submitted` 时由后端创建填报审核单。 */

export async function syncTaskToPortal(task) {

  if (!ctx.tenantId || !ctx.spaceId || task?.id == null) return null;

  try {

    const updated = await patchSubmissionTask(ctx.tenantId, ctx.spaceId, task.id, taskPatchPayload(task));

    Object.assign(task, normalizeSubmissionTask(updated));

    return task;

  } catch {

    return null;

  }

}

