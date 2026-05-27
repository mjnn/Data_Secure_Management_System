/**
 * 门户业务 API（审批 / 填报 / 绑定 / 字段目录）。
 * 依赖 usePortalTenantContext 解析 tenantId / spaceId。
 */
import api from "../api";
import { normalizeSubmissionTask, setBusinessFunctionCatalog } from "../data/submissionTasksMock.js";
import { setFieldCatalogCache } from "../stores/spaceConfigCache.js";

export const PORTAL_DATA_REFRESH_EVENT = "dsms-portal-data-refreshed";

/** 最近一次 API 拉取的任务列表，供字段目录等模块读取已审核填报明细 */
let portalTaskCache = [];

export function getPortalTaskCache() {
  return portalTaskCache;
}

function setPortalTaskCache(items) {
  portalTaskCache = items;
}

function upsertPortalTaskCache(task) {
  if (!task?.id) return;
  const idx = portalTaskCache.findIndex((t) => t.id === task.id);
  const normalized = normalizeSubmissionTask(task);
  if (idx >= 0) {
    portalTaskCache[idx] = normalized;
  } else {
    portalTaskCache.push(normalized);
  }
}

export function bumpPortalDataListeners() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(PORTAL_DATA_REFRESH_EVENT));
  }
}

function base(tenantId, spaceId) {
  return `/api/v1/dsms/tenants/${tenantId}/spaces/${spaceId}`;
}

export async function fetchBusinessFunctions(tenantId, spaceId) {
  const { data } = await api.get(`${base(tenantId, spaceId)}/business-functions`);
  const items = (data || []).map((f) => ({
    id: f.function_key,
    name: f.name,
    key: f.function_key,
    functionFoBound: !!f.has_active_fo_binding,
    foDisplay: f.requires_fo_binding ? "function_fo" : "",
    _apiId: f.id
  }));
  setBusinessFunctionCatalog(items);
  return items;
}

export async function fetchSubmissionTasks(tenantId, spaceId) {
  const { data } = await api.get(`${base(tenantId, spaceId)}/submission-tasks`, {
    params: { skip: 0, limit: 500 }
  });
  const items = (data?.items || []).map((t) => normalizeSubmissionTask(t));
  setPortalTaskCache(items);
  return items;
}

export async function fetchSubmissionTask(tenantId, spaceId, taskId) {
  const { data } = await api.get(`${base(tenantId, spaceId)}/submission-tasks/${taskId}`);
  const normalized = normalizeSubmissionTask(data);
  upsertPortalTaskCache(normalized);
  return normalized;
}

export async function createSubmissionTask(tenantId, spaceId, body) {
  const { data } = await api.post(`${base(tenantId, spaceId)}/submission-tasks`, body);
  bumpPortalDataListeners();
  return data;
}

export async function patchSubmissionTask(tenantId, spaceId, taskId, fields) {
  const { data } = await api.patch(`${base(tenantId, spaceId)}/submission-tasks/${taskId}`, { fields });
  const normalized = normalizeSubmissionTask(data);
  upsertPortalTaskCache(normalized);
  bumpPortalDataListeners();
  return normalized;
}

export async function dispatchSubmissionTasks(tenantId, spaceId, taskIds, dispatchNote) {
  const { data } = await api.post(`${base(tenantId, spaceId)}/submission-tasks/dispatch`, {
    task_ids: taskIds,
    dispatch_note: dispatchNote
  });
  bumpPortalDataListeners();
  return data;
}

export async function requestSubmissionCancel(tenantId, spaceId, taskId, reason) {
  const { data } = await api.post(
    `${base(tenantId, spaceId)}/submission-tasks/${taskId}/cancel-request?reason=${encodeURIComponent(reason)}`
  );
  bumpPortalDataListeners();
  return data;
}

export async function fetchApprovalRequests(tenantId, spaceId, params = {}) {
  const { data } = await api.get(`${base(tenantId, spaceId)}/approval-requests`, {
    params: { skip: 0, limit: 500, ...params }
  });
  return (data?.items || []).map((r) => ({
    ...r,
    id: String(r.id)
  }));
}

export async function approveApprovalRequest(tenantId, spaceId, requestId) {
  const { data } = await api.post(`${base(tenantId, spaceId)}/approval-requests/${requestId}/approve`);
  bumpPortalDataListeners();
  return data;
}

export async function rejectApprovalRequest(tenantId, spaceId, requestId, reason) {
  const { data } = await api.post(`${base(tenantId, spaceId)}/approval-requests/${requestId}/reject`, {
    reason
  });
  bumpPortalDataListeners();
  return data;
}

export async function fetchPendingApprovalCount(tenantId, spaceId) {
  const { data } = await api.get(`${base(tenantId, spaceId)}/approval-requests/pending-count`);
  return data?.count ?? 0;
}

export async function fetchMyFoBindings(tenantId, spaceId) {
  const { data } = await api.get(`${base(tenantId, spaceId)}/fo-function-bindings/me`);
  return data;
}

export async function submitFoBindingRequest(tenantId, spaceId, desiredFunctionKeys, reason) {
  const { data } = await api.post(`${base(tenantId, spaceId)}/fo-function-binding-requests`, {
    desired_function_keys: desiredFunctionKeys,
    reason
  });
  bumpPortalDataListeners();
  return data;
}

export async function fetchUserFoBindings(tenantId, spaceId, userId) {
  const { data } = await api.get(`${base(tenantId, spaceId)}/fo-function-bindings/users/${Number(userId)}`);
  return data;
}

export async function setUserFoBindings(tenantId, spaceId, userId, functionKeys) {
  const { data } = await api.put(`${base(tenantId, spaceId)}/fo-function-bindings/users/${Number(userId)}`, {
    function_keys: functionKeys
  });
  bumpPortalDataListeners();
  return data;
}

export async function submitFieldCatalogChangeRequest(tenantId, spaceId, body) {
  const { data } = await api.post(`${base(tenantId, spaceId)}/field-catalog-change-requests`, body);
  bumpPortalDataListeners();
  return data;
}

export async function fetchFieldCatalog(tenantId, spaceId) {
  const { data } = await api.get(`${base(tenantId, spaceId)}/field-catalog`, {
    params: { skip: 0, limit: 500 }
  });
  const items = (data?.items || []).map((e) => ({
    id: String(e.id),
    label: e.field_name,
    description: e.description || "",
    taxonomy_code: e.taxonomy_code || "",
    createdAt: e.created_at?.slice?.(0, 10) || "",
    updatedAt: e.updated_at?.slice?.(0, 10) || e.created_at?.slice?.(0, 10) || "",
    _apiId: e.id,
    identifier_key: e.identifier_key
  }));
  setFieldCatalogCache(items);
  return items;
}

export async function createFieldCatalogEntry(tenantId, spaceId, entry) {
  const { data } = await api.post(`${base(tenantId, spaceId)}/field-catalog`, {
    field_name: entry.label,
    description: entry.description || null,
    identifier_key: entry.identifier_key || entry.label.toLowerCase().replace(/\s+/g, "_"),
    data_type: "string",
    taxonomy_code: entry.taxonomy_code || null
  });
  bumpPortalDataListeners();
  return data;
}

export async function updateFieldCatalogEntry(tenantId, spaceId, entryId, entry) {
  const { data } = await api.put(`${base(tenantId, spaceId)}/field-catalog/${entryId}`, {
    field_name: entry.label,
    identifier_key: entry.identifier_key,
    data_type: "string",
    description: entry.description || null,
    taxonomy_code: entry.taxonomy_code || null
  });
  bumpPortalDataListeners();
  return data;
}

export async function deleteFieldCatalogEntry(tenantId, spaceId, entryId) {
  const { data } = await api.delete(`${base(tenantId, spaceId)}/field-catalog/${entryId}`);
  bumpPortalDataListeners();
  return data;
}

/** 字段目录 pending 申请（来自 approval 表） */
export async function fetchPendingFieldCatalogApprovals(tenantId, spaceId) {
  const all = await fetchApprovalRequests(tenantId, spaceId, { status: "pending" });
  return all.filter(
    (r) => r.type === "field_catalog_create" || r.type === "field_catalog_delete"
  );
}
