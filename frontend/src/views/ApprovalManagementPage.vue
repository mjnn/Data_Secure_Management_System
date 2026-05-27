<template>
  <section class="apm dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="apm-title">
    <header class="apm__header dsms-animate-stagger-1">
      <h2 id="apm-title" class="apm__title">审批管理</h2>
      <p v-if="isSystemAdmin" class="apm__lead">
        系统管理员：处理功能 FO 提交的各类申请，并审核已提交的填报内容；下方为<strong>全角色审批链</strong>说明。
      </p>
      <p v-else-if="isSecurityFoReviewer" class="apm__lead">
        数据安全 FO：处理功能 FO 提交的各类申请，并审核已提交的填报内容。
      </p>
      <p v-else-if="isFunctionFo" class="apm__lead">
        功能 FO：查看本人提交的绑定变更、数据字段、取消填报等申请进度；审批由数据安全 FO 在「待我审批」中处理（您无审批权限）。
      </p>
    </header>

    <el-card v-if="isSystemAdmin" class="apm__chains dsms-animate-stagger-2" shadow="never">
      <template #header>
        <span class="apm__card-title">审批链一览</span>
      </template>
      <el-table :data="approvalChains" border stripe size="small" class="apm__chain-table">
        <el-table-column prop="title" label="事项" min-width="140" show-overflow-tooltip />
        <el-table-column prop="applicantRole" label="发起方" width="120" />
        <el-table-column prop="approverRole" label="审批方" width="120" />
        <el-table-column prop="trigger" label="触发条件" min-width="200" show-overflow-tooltip />
        <el-table-column prop="outcome" label="通过后" min-width="160" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-tabs v-model="activeTab" class="apm__tabs dsms-animate-stagger-3">
      <div class="apm__record-toolbar">
        <el-form :inline="true" class="apm__filters" @submit.prevent>
          <el-form-item label="关键词">
            <el-input
              v-model="searchKeyword"
              clearable
              placeholder="类型、摘要、申请人、审批人、状态、时间…"
              style="width: 280px"
              aria-label="搜索审批记录"
            />
          </el-form-item>
          <el-form-item v-if="activeTab === 'mine' || activeTab === 'all'" label="状态">
            <dsms-filterable-select
              v-model="statusFilter"
              clearable
              placeholder="全部状态"
              style="width: 140px"
              aria-label="按状态筛选"
            >
              <el-option label="待审批" :value="APPROVAL_STATUS_PENDING" />
              <el-option label="已通过" :value="APPROVAL_STATUS_APPROVED" />
              <el-option label="已驳回" :value="APPROVAL_STATUS_REJECTED" />
            </dsms-filterable-select>
          </el-form-item>
          <el-form-item>
            <el-button @click="resetRecordFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-tab-pane v-if="isReviewer" :label="`待我审批 (${pendingFiltered.length})`" name="pending">
        <el-table :data="pendingFiltered" border stripe :empty-text="recordEmptyText(pendingFiltered.length, pendingRows.length)">
          <el-table-column prop="requestedAt" label="申请时间" width="168" />
          <el-table-column label="类型" width="140">
            <template #default="{ row }">{{ approvalTypeLabel(row.type) }}</template>
          </el-table-column>
          <el-table-column prop="title" label="摘要" min-width="220" show-overflow-tooltip />
          <el-table-column prop="requestedBy" label="申请人" width="110" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="onApprove(row)">通过</el-button>
              <el-button link type="danger" @click="onReject(row)">驳回</el-button>
              <el-button
                v-if="row.type === APPROVAL_TYPE_SUBMISSION_REVIEW"
                link
                type="primary"
                @click="goTaskDetail(row)"
              >
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="`我的申请 (${myApplicationFiltered.length})`" name="mine">
        <el-table :data="myApplicationFiltered" border stripe :empty-text="recordEmptyText(myApplicationFiltered.length, myApplicationRows.length)">
          <el-table-column prop="requestedAt" label="申请时间" width="168" />
          <el-table-column label="类型" width="140">
            <template #default="{ row }">{{ approvalTypeLabel(row.type) }}</template>
          </el-table-column>
          <el-table-column prop="title" label="摘要" min-width="200" show-overflow-tooltip />
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ approvalStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reviewedAt" label="处理时间" width="168">
            <template #default="{ row }">{{ row.reviewedAt || "—" }}</template>
          </el-table-column>
          <el-table-column prop="rejectReason" label="驳回理由" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.rejectReason || "—" }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane v-if="isReviewer" :label="`全部记录 (${allFiltered.length})`" name="all">
        <el-table :data="allFiltered" border stripe :empty-text="recordEmptyText(allFiltered.length, allRows.length)">
          <el-table-column prop="requestedAt" label="申请时间" width="168" />
          <el-table-column label="类型" width="130">
            <template #default="{ row }">{{ approvalTypeLabel(row.type) }}</template>
          </el-table-column>
          <el-table-column prop="title" label="摘要" min-width="180" show-overflow-tooltip />
          <el-table-column prop="requestedBy" label="申请人" width="100" />
          <el-table-column label="状态" width="96" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ approvalStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reviewedBy" label="审批人" width="110">
            <template #default="{ row }">{{ row.reviewedBy || "—" }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import { APPROVAL_CHAIN_ROWS } from "../data/approvalChains.js";
import { ensurePortalTenantReady, usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import {
  APPROVAL_STATUS_APPROVED,
  APPROVAL_STATUS_PENDING,
  APPROVAL_STATUS_REJECTED,
  approvalStatusLabel,
  approvalTypeLabel
} from "../data/approvalRequestsMock.js";
import {
  approveApprovalRequest,
  fetchApprovalRequests,
  PORTAL_DATA_REFRESH_EVENT,
  rejectApprovalRequest
} from "../api/portalApi.js";

const APPROVAL_TYPE_SUBMISSION_REVIEW = "submission_fill_review";

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const { user: me, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();
const allRequests = ref([]);
const loading = ref(false);
const activeTab = ref("pending");
const searchKeyword = ref("");
const statusFilter = ref("");

const approvalChains = APPROVAL_CHAIN_ROWS;

const isReviewer = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

const isSystemAdmin = computed(() => effectivePlatformRole(me.value) === PLATFORM_ROLE.SYSTEM_ADMIN);

const isSecurityFoReviewer = computed(
  () => effectivePlatformRole(me.value) === PLATFORM_ROLE.SECURITY_FO
);

const isFunctionFo = computed(() => effectivePlatformRole(me.value) === PLATFORM_ROLE.FUNCTION_FO);

const pendingRows = computed(() => {
  if (!isReviewer.value) return [];
  return allRequests.value.filter((r) => r.status === APPROVAL_STATUS_PENDING);
});

const myApplicationRows = computed(() => {
  if (!me.value) return [];
  const uid = me.value.id;
  return allRequests.value
    .filter((r) => r.requester_user_id === uid)
    .slice()
    .sort((a, b) => String(b.requestedAt).localeCompare(String(a.requestedAt)));
});

const allRows = computed(() =>
  allRequests.value.slice().sort((a, b) => String(b.requestedAt).localeCompare(String(a.requestedAt)))
);

function approvalSearchHaystack(row) {
  return [
    row.title,
    approvalTypeLabel(row.type),
    approvalStatusLabel(row.status),
    row.requestedBy,
    row.reviewedBy,
    row.rejectReason,
    row.requestedAt,
    row.reviewedAt,
    row.payload?.reason,
    row.payload?.proposedLabel,
    row.payload?.proposedDescription,
    row.payload?.task_id != null ? String(row.payload.task_id) : row.payload?.taskId != null ? String(row.payload.taskId) : ""
  ]
    .filter((x) => x != null && String(x).length)
    .join(" ")
    .toLowerCase();
}

function filterApprovalRecords(rows) {
  let list = rows;
  const sf = statusFilter.value;
  if (sf && (activeTab.value === "mine" || activeTab.value === "all")) {
    list = list.filter((r) => r.status === sf);
  }
  const q = searchKeyword.value.trim().toLowerCase();
  if (!q) return list;
  return list.filter((r) => approvalSearchHaystack(r).includes(q));
}

const pendingFiltered = computed(() => filterApprovalRecords(pendingRows.value));
const myApplicationFiltered = computed(() => filterApprovalRecords(myApplicationRows.value));
const allFiltered = computed(() => filterApprovalRecords(allRows.value));

function recordEmptyText(filteredLen, totalLen) {
  if (totalLen === 0) {
    if (activeTab.value === "pending") return "暂无待审批事项";
    if (activeTab.value === "mine") return "暂无申请记录";
    return "暂无记录";
  }
  if (filteredLen === 0) return "无匹配记录，请调整关键词或状态筛选";
  return "暂无记录";
}

function resetRecordFilters() {
  searchKeyword.value = "";
  statusFilter.value = "";
}

function bump() {
  loadApprovals();
}

async function loadApprovals() {
  if (!ready.value || !tenantId.value) return;
  loading.value = true;
  try {
    allRequests.value = await fetchApprovalRequests(tenantId.value, spaceId.value);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载审批记录失败");
  } finally {
    loading.value = false;
  }
}

function statusTagType(status) {
  if (status === APPROVAL_STATUS_APPROVED) return "success";
  if (status === APPROVAL_STATUS_REJECTED) return "danger";
  return "warning";
}

async function onApprove(row) {
  try {
    await ElMessageBox.confirm(`确定通过「${row.title}」吗？`, "审批通过", {
      type: "info",
      confirmButtonText: "通过",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  try {
    const data = await approveApprovalRequest(tenantId.value, spaceId.value, row.id);
    ElMessage.success(data.message || "已通过");
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "操作失败");
    return;
  }
  bump();
}

async function onReject(row) {
  let reason = "";
  try {
    const { value } = await ElMessageBox.prompt("请输入驳回理由", "驳回申请", {
      confirmButtonText: "驳回",
      cancelButtonText: "取消",
      inputValidator: (v) => (String(v || "").trim() ? true : "请填写驳回理由")
    });
    reason = String(value || "").trim();
  } catch {
    return;
  }
  try {
    const data = await rejectApprovalRequest(tenantId.value, spaceId.value, row.id, reason);
    ElMessage.success(data.message || "已驳回");
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "操作失败");
    return;
  }
  bump();
}

function goTaskDetail(row) {
  const taskId = row.payload?.task_id ?? row.payload?.taskId;
  if (taskId != null) {
    router.push({ name: "dashboard-submission-task-detail", params: { taskId: String(taskId) } });
  }
}

onMounted(async () => {
  await Promise.all([ensureCurrentUser(), ensurePortalTenantReady()]);
  if (isFunctionFo.value) activeTab.value = "mine";
  await loadApprovals();
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, bump);
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, bump);
});
</script>

<style scoped>
.apm {
  padding: 24px 28px 32px;
}

.apm__header {
  margin-bottom: 20px;
}

.apm__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.apm__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.apm__chains {
  margin-bottom: 20px;
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.apm__card-title {
  font-weight: 600;
}

.apm__chain-table {
  width: 100%;
}

.apm__tabs {
  margin-top: 8px;
}

.apm__record-toolbar {
  margin-bottom: 12px;
}

.apm__filters :deep(.el-form-item) {
  margin-bottom: 8px;
}
</style>
