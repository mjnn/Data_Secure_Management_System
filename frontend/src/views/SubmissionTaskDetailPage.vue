<template>
  <section class="std dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="std-title">
    <header class="std__header dsms-animate-stagger-1">
      <el-button text type="primary" class="std__back" @click="goBack">
        <span aria-hidden="true">←</span> 返回任务列表
      </el-button>
      <h2 id="std-title" class="std__title">填报任务详情</h2>
      <p v-if="!me" class="std__lead">正在加载当前用户…</p>
      <p v-else-if="!task" class="std__lead">未找到该任务，可能已被删除或链接无效。</p>
      <p v-else class="std__lead">
        查看任务基本信息、各执行人<strong>填报表单（只读）</strong>与<strong>功能 FO 填报情况</strong>汇总；对已提交填报的任务可进行<strong>审核</strong>（模拟）。表单字段与布局待「填报流程」定稿后由接口下发，本页按快照数据渲染。
      </p>
    </header>

    <template v-if="me && isSecOrAdmin && task">
      <el-descriptions class="std__desc dsms-animate-stagger-2" :column="2" border size="small" title="任务信息">
        <el-descriptions-item label="任务名称">{{ task.title }}</el-descriptions-item>
        <el-descriptions-item label="业务功能">{{ submissionFunctionName(task.functionId) }}</el-descriptions-item>
        <el-descriptions-item label="任务状态">
          <el-tag :type="task.status === 'dispatched' ? 'success' : 'info'" size="small">
            {{ task.status === "dispatched" ? "已下发" : "草稿" }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ task.createdAt }}</el-descriptions-item>
        <el-descriptions-item label="下发时间">{{ task.dispatchedAt || "—" }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ task.internalNote || "—" }}</el-descriptions-item>
        <el-descriptions-item label="填报任务说明" :span="2">
          {{ task.dispatchNote || "—" }}
        </el-descriptions-item>
      </el-descriptions>

      <h3 class="std__h3">功能 FO 填报情况</h3>
      <p class="std__sub">
        以下为绑定至该业务功能的执行侧填报进度汇总（含主责与协同等<strong>模拟</strong>多行；后续由接口按真实责任人展开）。
      </p>
      <el-table class="std__table" :data="assigneeRows" border stripe size="small" empty-text="暂无填报人数据">
        <el-table-column prop="label" label="执行人 / 角色" min-width="200" show-overflow-tooltip />
        <el-table-column label="进度" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.foCancellationRequested" type="warning" size="small">取消申请中</el-tag>
            <el-tag v-else :type="progressTag(row.foFillStatus)" size="small">{{ progressLabel(row.foFillStatus) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="取消理由" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.foCancellationRequested ? row.foCancellationReason || "—" : "—" }}
          </template>
        </el-table-column>
        <el-table-column label="填报摘要" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.foFillContentSummary || "—" }}
          </template>
        </el-table-column>
      </el-table>

      <h3 class="std__h3">功能 FO 填报表单（只读）</h3>
      <p class="std__sub">
        数据安全 FO / 系统管理员在此查看各执行人填报的<strong>具体表单内容</strong>（结构化快照）。正式环境中内容由填报流程定义并与动态表单引擎对齐；当前为模拟快照字段。
      </p>
      <div v-for="row in assigneeRows" :key="`${row.key}-form`" class="std__form-assignee">
        <el-divider content-position="left">{{ row.label }}</el-divider>
        <template v-if="row.foFillStatus === 'not_started' && !row.foCancellationRequested">
          <el-empty description="尚未开始填报，无表单数据" :image-size="56" />
        </template>
        <template v-else-if="row.foCancellationRequested && row.foFillStatus !== 'submitted'">
          <el-alert
            type="warning"
            :closable="false"
            show-icon
            title="取消申请处理中"
            description="表单内容以只读保留；审批结果以接口为准。"
          />
        </template>
        <template v-else-if="hasRenderableFormSnapshot(row.formSnapshot)">
          <div class="std__form-body">
            <SubmissionFillFormReadonly :snapshot="row.formSnapshot" />
          </div>
        </template>
        <template v-else-if="row.foFillStatus === 'draft' || row.foFillStatus === 'submitted'">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="表单结构待接口下发"
            description="当前执行人进度为草稿或已提交，但尚无结构化表单快照。填报流程定义并落库后，此处将只读展示功能 FO 填报的完整控件与取值。"
          />
        </template>
        <template v-else>
          <el-empty description="暂无表单展示" :image-size="56" />
        </template>
      </div>

      <template v-if="canAudit">
        <h3 class="std__h3">审核</h3>
        <el-alert
          v-if="auditStatusLabel"
          class="std__audit-alert"
          :title="`当前审核状态：${auditStatusLabel}`"
          :type="task.auditStatus === 'approved' ? 'success' : task.auditStatus === 'returned' ? 'warning' : 'info'"
          :closable="false"
          show-icon
        >
          <template v-if="task.auditComment">
            <p class="std__audit-note">审核说明：{{ task.auditComment }}</p>
          </template>
          <p v-if="task.auditedAt" class="std__audit-note">审核时间：{{ task.auditedAt }}</p>
        </el-alert>
        <div v-if="task.auditStatus == null || task.auditStatus === 'pending' || task.auditStatus === ''" class="std__audit-actions">
          <el-button type="primary" @click="onApprove">审核通过</el-button>
          <el-button type="warning" plain @click="openReturnDialog">退回修改</el-button>
        </div>
      </template>
      <el-alert
        v-else-if="task.status === 'dispatched'"
        class="std__audit-alert"
        type="info"
        :closable="false"
        show-icon
        title="暂不可审核"
        description="仅当功能 FO 已提交填报且未处于取消申请中时，数据安全侧可进行审核。"
      />
    </template>

    <el-dialog v-model="returnVisible" title="退回修改" width="480px" destroy-on-close append-to-body @closed="resetReturn">
      <el-form ref="returnFormRef" :model="returnForm" :rules="returnRules" label-position="top">
        <el-form-item label="退回说明" prop="comment">
          <el-input
            v-model="returnForm.comment"
            type="textarea"
            :rows="4"
            maxlength="1000"
            show-word-limit
            placeholder="请说明退回原因（必填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="returnVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReturn">确认退回</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "../api";
import {
  hasRenderableFormSnapshot,
  loadSubmissionTasksMerged,
  normalizeSubmissionTask,
  submissionFunctionById,
  submissionFunctionName,
  SUBMISSION_TASKS_STORAGE_KEY
} from "../data/submissionTasksMock";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";
import { bumpSubmissionTaskPersistListeners } from "../composables/useSubmissionTaskFoReminderCount";
import SubmissionFillFormReadonly from "../components/SubmissionFillFormReadonly.vue";

const route = useRoute();
const router = useRouter();
const me = ref(null);
const tasks = ref([]);

const taskId = computed(() => {
  const raw = route.params.taskId;
  const n = Number(raw);
  return Number.isFinite(n) ? n : NaN;
});

const task = computed(() => {
  if (!Number.isFinite(taskId.value)) return null;
  return tasks.value.find((t) => t.id === taskId.value) || null;
});

const platformRole = computed(() => effectivePlatformRole(me.value));
const isSecOrAdmin = computed(
  () => platformRole.value === PLATFORM_ROLE.SYSTEM_ADMIN || platformRole.value === PLATFORM_ROLE.SECURITY_FO
);

const assigneeRows = computed(() => {
  const t = task.value;
  if (!t) return [];
  const fn = submissionFunctionById(t.functionId);
  const primaryLabel = fn?.functionFoBound
    ? `绑定功能 FO（${submissionFunctionName(t.functionId)}）`
    : `功能 FO（${submissionFunctionName(t.functionId)}）`;
  const primary = {
    key: "primary",
    label: primaryLabel,
    foFillStatus: t.foCancellationRequested ? "cancel_pending" : t.foFillStatus || "not_started",
    foCancellationRequested: !!t.foCancellationRequested,
    foCancellationReason: t.foCancellationReason || "",
    foFillContentSummary: t.foFillContentSummary || "",
    formSnapshot: t.foFillFormSnapshot ?? null
  };
  const extras = Array.isArray(t.foExtraAssignees) ? t.foExtraAssignees : [];
  const mapped = extras.map((r, i) => ({
    key: `extra-${i}`,
    label: r.label || `协同（${i + 1}）`,
    foFillStatus: r.foCancellationRequested ? "cancel_pending" : r.foFillStatus || "not_started",
    foCancellationRequested: !!r.foCancellationRequested,
    foCancellationReason: r.foCancellationReason || "",
    foFillContentSummary: r.foFillContentSummary || "",
    formSnapshot: r.foFillFormSnapshot ?? null
  }));
  return [primary, ...mapped];
});

const canAudit = computed(() => {
  const t = task.value;
  if (!t || t.status !== "dispatched") return false;
  if (t.foCancellationRequested) return false;
  return t.foFillStatus === "submitted";
});

const auditStatusLabel = computed(() => {
  const t = task.value;
  if (!t) return "";
  const s = t.auditStatus;
  if (s === "approved") return "已通过";
  if (s === "returned") return "已退回";
  if (s === "pending") return "待审核";
  if (t.status === "dispatched" && !t.foCancellationRequested && t.foFillStatus === "submitted" && (s == null || s === "")) {
    return "待审核";
  }
  return "";
});

function progressLabel(s) {
  if (s === "cancel_pending") return "取消申请中";
  if (s === "draft") return "草稿";
  if (s === "submitted") return "已提交";
  return "未填报";
}

function progressTag(s) {
  if (s === "submitted") return "success";
  if (s === "draft" || s === "cancel_pending") return "warning";
  return "info";
}

function loadTasks() {
  tasks.value = loadSubmissionTasksMerged();
}

function persistTasks() {
  try {
    sessionStorage.setItem(SUBMISSION_TASKS_STORAGE_KEY, JSON.stringify(tasks.value));
  } catch (_e) {
    /* ignore */
  }
  bumpSubmissionTaskPersistListeners();
}

function goBack() {
  router.push({ name: "dashboard-submission-task" });
}

const loadMe = async () => {
  try {
    const { data } = await api.get("/api/v1/users/me");
    me.value = data;
    const role = effectivePlatformRole(data);
    if (role !== PLATFORM_ROLE.SYSTEM_ADMIN && role !== PLATFORM_ROLE.SECURITY_FO) {
      ElMessage.warning("当前角色无权访问填报任务审核详情。");
      await router.replace({ name: "dashboard-submission-task" });
    }
  } catch {
    /* 未登录由全局守卫处理 */
  }
};

onMounted(() => {
  loadTasks();
  loadMe();
});

watch(
  () => route.params.taskId,
  () => {
    loadTasks();
  }
);

function onApprove() {
  const t = task.value;
  if (!t) return;
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  t.auditStatus = "approved";
  t.auditComment = "";
  t.auditedAt = now;
  persistTasks();
  ElMessage.success("审核通过（模拟）。");
}

const returnVisible = ref(false);
const returnFormRef = ref(null);
const returnForm = reactive({ comment: "" });
const returnRules = {
  comment: [{ required: true, message: "请填写退回说明", trigger: "blur" }]
};

function openReturnDialog() {
  returnForm.comment = "";
  returnVisible.value = true;
}

function resetReturn() {
  returnFormRef.value?.clearValidate?.();
}

async function submitReturn() {
  const form = returnFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  const t = task.value;
  if (!t) return;
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  t.auditStatus = "returned";
  t.auditComment = returnForm.comment.trim();
  t.auditedAt = now;
  persistTasks();
  returnVisible.value = false;
  ElMessage.success("已退回修改（模拟）。");
}
</script>

<style scoped>
.std {
  padding: 24px 28px 32px;
}

.std__header {
  margin-bottom: 20px;
}

.std__back {
  padding: 0 0 12px;
  font-size: 0.875rem;
}

.std__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.std__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.std__desc {
  margin-bottom: 24px;
}

.std__h3 {
  margin: 24px 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.std__sub {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--dsms-text-secondary);
}

.std__table {
  width: 100%;
}

.std__audit-alert {
  margin-bottom: 12px;
}

.std__audit-note {
  margin: 6px 0 0;
  font-size: 0.8125rem;
  line-height: 1.45;
}

.std__audit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}

.std__form-assignee {
  margin-bottom: 8px;
}

.std__form-body {
  padding: 0 0 8px;
}
</style>
