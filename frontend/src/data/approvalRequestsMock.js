/**
 * 审批类型与状态常量（展示用）；审批数据以 portal API 为真源。
 */

import { chainMetaForType } from "./approvalChains.js";

export const APPROVAL_STATUS_PENDING = "pending";
export const APPROVAL_STATUS_APPROVED = "approved";
export const APPROVAL_STATUS_REJECTED = "rejected";

export const APPROVAL_TYPE_FO_FUNCTION_BINDING = "fo_function_binding";
export const APPROVAL_TYPE_FIELD_CATALOG_CREATE = "field_catalog_create";
export const APPROVAL_TYPE_FIELD_CATALOG_DELETE = "field_catalog_delete";
export const APPROVAL_TYPE_SUBMISSION_CANCEL = "submission_fill_cancel";
export const APPROVAL_TYPE_SUBMISSION_REVIEW = "submission_fill_review";

export const APPROVAL_TYPE_LABELS = {
  [APPROVAL_TYPE_FO_FUNCTION_BINDING]: "业务功能绑定变更",
  [APPROVAL_TYPE_FIELD_CATALOG_CREATE]: "数据字段新增",
  [APPROVAL_TYPE_FIELD_CATALOG_DELETE]: "数据字段删除",
  [APPROVAL_TYPE_SUBMISSION_CANCEL]: "取消填报任务",
  [APPROVAL_TYPE_SUBMISSION_REVIEW]: "填报内容审核"
};

export function approvalStatusLabel(status) {
  if (status === APPROVAL_STATUS_APPROVED) return "已通过";
  if (status === APPROVAL_STATUS_REJECTED) return "已驳回";
  return "待审批";
}

export function approvalTypeLabel(type) {
  return APPROVAL_TYPE_LABELS[type] || chainMetaForType(type)?.title || type;
}
