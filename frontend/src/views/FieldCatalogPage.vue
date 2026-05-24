<template>
  <section class="fcp dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="fcp-title">
    <header class="fcp__header dsms-animate-stagger-1">
      <h2 id="fcp-title" class="fcp__title">数据字段</h2>
      <p v-if="!me" class="fcp__lead">正在加载当前用户…</p>
      <template v-else-if="isSecOrAdmin">
        <p class="fcp__lead">
          维护动态表单中「数据字段」单选的下拉选项；关联业务功能清单来自<strong>已审核通过</strong>的填报任务明细（<code class="fcp__code">foFillLifecycleRows</code> 中
          <code class="fcp__code">data_field</code> × <code class="fcp__code">business_function</code>）。功能 FO 对新增/删除须提交申请，在本页下方<strong>待处理申请</strong>中审核。
        </p>
      </template>
      <template v-else-if="isFunctionFo">
        <p class="fcp__lead">
          <strong>{{ boundFunctionNames }}（业务功能）</strong>涉及的数据字段：下列条目来自<strong>已通过审核</strong>的填报记录，且与您绑定的业务功能有关联；新增或删除目录项请提交申请，由数据安全侧审核。
        </p>
      </template>
      <p v-else class="fcp__lead">当前角色无此页访问说明。</p>
    </header>

    <template v-if="me && (isSecOrAdmin || isFunctionFo)">
      <template v-if="isSecOrAdmin">
        <div class="fcp__toolbar dsms-animate-stagger-2">
          <el-button type="primary" @click="openSecCreate">新增数据字段</el-button>
        </div>

        <el-table
          class="fcp__table dsms-animate-stagger-2"
          :data="secCatalogRows"
          border
          stripe
          empty-text="暂无数据字段"
        >
          <el-table-column prop="label" label="数据字段名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="description" label="说明" min-width="140" show-overflow-tooltip />
          <el-table-column label="关联业务功能（已审核填报）" min-width="260">
            <template #default="{ row }">
              {{ formatRelatedAll(row.label) }}
            </template>
          </el-table-column>
          <el-table-column label="创建 / 更新" width="200">
            <template #default="{ row }">
              {{ row.createdAt }} / {{ row.updatedAt }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openSecEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="onSecDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-card class="fcp__card dsms-animate-stagger-3" shadow="never">
          <template #header>
            <span class="fcp__card-title">待处理申请</span>
          </template>
          <el-table :data="pendingRequests" border stripe empty-text="暂无待处理申请">
            <el-table-column prop="requestedAt" label="申请时间" width="170" />
            <el-table-column prop="requestedBy" label="申请人" width="120" show-overflow-tooltip />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                {{ row.type === "create" ? "新增" : row.type === "delete" ? "删除" : row.type }}
              </template>
            </el-table-column>
            <el-table-column label="内容" min-width="220">
              <template #default="{ row }">
                <template v-if="row.type === 'create'">{{ row.proposedLabel }}</template>
                <template v-else>{{ deleteRequestLabel(row) }}</template>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="onApprove(row)">通过</el-button>
                <el-button link type="danger" @click="onReject(row)">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </template>

      <template v-else>
        <div class="fcp__toolbar dsms-animate-stagger-2">
          <el-button type="primary" @click="openFoCreateRequest">申请新增数据字段</el-button>
        </div>

        <el-table
          class="fcp__table dsms-animate-stagger-2"
          :data="foCatalogRows"
          border
          stripe
          :empty-text="foEmptyText"
        >
          <el-table-column prop="label" label="数据字段名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="description" label="说明" min-width="140" show-overflow-tooltip />
          <el-table-column label="关联业务功能（与您相关）" min-width="220">
            <template #default="{ row }">
              {{ relatedNamesForBound(row.label) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="danger" :disabled="hasPendingDelete(row.id)" @click="submitDeleteRequest(row)">
                申请删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-card class="fcp__card dsms-animate-stagger-4" shadow="never">
          <template #header>
            <span class="fcp__card-title">我的申请</span>
          </template>
          <el-table :data="myRequests" border stripe empty-text="暂无申请记录">
            <el-table-column prop="requestedAt" label="申请时间" width="170" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                {{ row.type === "create" ? "新增" : row.type === "delete" ? "删除" : row.type }}
              </template>
            </el-table-column>
            <el-table-column label="内容" min-width="200">
              <template #default="{ row }">
                <template v-if="row.type === 'create'">{{ row.proposedLabel }}</template>
                <template v-else>{{ deleteRequestLabel(row) }}</template>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                {{ statusLabel(row.status) }}
              </template>
            </el-table-column>
            <el-table-column prop="reviewedAt" label="处理时间" width="170" />
            <el-table-column prop="rejectReason" label="驳回原因" min-width="140" show-overflow-tooltip />
          </el-table>
        </el-card>
      </template>
    </template>

    <el-dialog v-model="secEditVisible" :title="secEditMode === 'create' ? '新增数据字段' : '编辑数据字段'" width="480px" @closed="resetSecEdit">
      <el-form ref="secFormRef" :model="secForm" :rules="secRules" label-width="100px">
        <el-form-item label="名称" prop="label">
          <el-input v-model="secForm.label" maxlength="200" show-word-limit placeholder="须全局唯一" />
        </el-form-item>
        <el-form-item label="说明" prop="description">
          <el-input v-model="secForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="secEditVisible = false">取消</el-button>
        <el-button type="primary" @click="submitSecEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="foCreateVisible" title="申请新增数据字段" width="480px" @closed="resetFoCreate">
      <el-form ref="foCreateFormRef" :model="foCreateForm" :rules="foCreateRules" label-width="100px">
        <el-form-item label="名称" prop="label">
          <el-input v-model="foCreateForm.label" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="说明" prop="description">
          <el-input v-model="foCreateForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="foCreateVisible = false">取消</el-button>
        <el-button type="primary" @click="submitFoCreateRequest">提交申请</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import api from "../api";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";
import { MOCK_FO_BOUND_FUNCTION_IDS } from "../composables/useSubmissionTaskFoReminderCount";
import {
  addDataFieldCatalogEntryDirect,
  aggregateDataFieldLabelToFunctionIdsFromApprovedSubmissions,
  approveCatalogRequest,
  DATA_FIELD_CATALOG_PERSIST_EVENT,
  filterCatalogEntriesForFunctionFo,
  formatRelatedFunctionNames as formatRelatedFunctionNamesFromCatalog,
  loadCatalogRequests,
  loadDataFieldCatalogEntries,
  rejectCatalogRequest,
  removeDataFieldCatalogEntryDirect,
  submitCatalogRequest,
  updateDataFieldCatalogEntryDirect
} from "../data/dataFieldCatalogMock.js";
import { submissionFunctionName } from "../data/submissionTasksMock.js";

const me = ref(null);
const refreshTick = ref(0);

const isSecOrAdmin = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

const isFunctionFo = computed(() => effectivePlatformRole(me.value) === PLATFORM_ROLE.FUNCTION_FO);

const boundFunctionNames = computed(() =>
  MOCK_FO_BOUND_FUNCTION_IDS.map((id) => submissionFunctionName(id)).join("、")
);

function bumpLocal() {
  refreshTick.value++;
}

function relatedNamesForBound(label) {
  void refreshTick.value;
  const m = aggregateDataFieldLabelToFunctionIdsFromApprovedSubmissions();
  const set = m.get(String(label || "").trim());
  if (!set || !set.size) return "—";
  const bound = new Set(MOCK_FO_BOUND_FUNCTION_IDS);
  const names = [...set].filter((id) => bound.has(id)).map((id) => submissionFunctionName(id));
  return names.length ? names.join("、") : "—";
}

function formatRelatedAll(label) {
  void refreshTick.value;
  return formatRelatedFunctionNamesFromCatalog(label);
}

const secCatalogRows = computed(() => {
  void refreshTick.value;
  return [...loadDataFieldCatalogEntries()].sort((a, b) =>
    String(a.label || "").localeCompare(String(b.label || ""), "zh-Hans-CN")
  );
});

const foCatalogRows = computed(() => {
  void refreshTick.value;
  return filterCatalogEntriesForFunctionFo(MOCK_FO_BOUND_FUNCTION_IDS).sort((a, b) =>
    String(a.label || "").localeCompare(String(b.label || ""), "zh-Hans-CN")
  );
});

const foEmptyText = computed(() =>
  foCatalogRows.value.length ? "" : "暂无与您绑定业务功能相关、且来源于已审核填报的数据字段"
);

const pendingRequests = computed(() => {
  void refreshTick.value;
  return loadCatalogRequests().filter((r) => r.status === "pending");
});

const myRequests = computed(() => {
  void refreshTick.value;
  const u = me.value?.username;
  if (!u) return [];
  return loadCatalogRequests()
    .filter((r) => r.requestedBy === u)
    .slice()
    .reverse();
});

function hasPendingDelete(catalogEntryId) {
  void refreshTick.value;
  return loadCatalogRequests().some(
    (r) => r.status === "pending" && r.type === "delete" && r.catalogEntryId === catalogEntryId
  );
}

function deleteRequestLabel(req) {
  void refreshTick.value;
  if (req.type !== "delete" || !req.catalogEntryId) return "—";
  const e = loadDataFieldCatalogEntries().find((x) => x.id === req.catalogEntryId);
  return e ? `删除：${e.label}` : `删除：${req.catalogEntryId}`;
}

function statusLabel(s) {
  if (s === "pending") return "待审核";
  if (s === "approved") return "已通过";
  if (s === "rejected") return "已驳回";
  return s || "—";
}

const secEditVisible = ref(false);
const secEditMode = ref("create");
const secEditingId = ref("");
const secFormRef = ref(null);
const secForm = ref({ label: "", description: "" });

const secRules = {
  label: [{ required: true, message: "请输入数据字段名称", trigger: "blur" }]
};

function openSecCreate() {
  secEditMode.value = "create";
  secEditingId.value = "";
  secForm.value = { label: "", description: "" };
  secEditVisible.value = true;
}

function openSecEdit(row) {
  secEditMode.value = "edit";
  secEditingId.value = row.id;
  secForm.value = { label: row.label || "", description: row.description || "" };
  secEditVisible.value = true;
}

function resetSecEdit() {
  secFormRef.value?.clearValidate?.();
}

async function submitSecEdit() {
  const form = secFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  if (secEditMode.value === "create") {
    const res = addDataFieldCatalogEntryDirect({
      label: secForm.value.label,
      description: secForm.value.description
    });
    if (!res.ok) {
      ElMessage.error(res.message);
      return;
    }
    ElMessage.success(res.message);
  } else {
    const res = updateDataFieldCatalogEntryDirect(secEditingId.value, {
      label: secForm.value.label,
      description: secForm.value.description
    });
    if (!res.ok) {
      ElMessage.error(res.message);
      return;
    }
    ElMessage.success(res.message);
  }
  secEditVisible.value = false;
  bumpLocal();
}

async function onSecDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除数据字段「${row.label}」吗？删除后填报下拉将不再包含该项。`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  const res = removeDataFieldCatalogEntryDirect(row.id);
  if (!res.ok) {
    ElMessage.error(res.message);
    return;
  }
  ElMessage.success(res.message);
  bumpLocal();
}

async function onApprove(row) {
  const res = approveCatalogRequest(row.id);
  if (!res.ok) {
    ElMessage.error(res.message);
    return;
  }
  ElMessage.success(res.message);
  bumpLocal();
}

async function onReject(row) {
  let reason = "";
  try {
    const { value } = await ElMessageBox.prompt("请输入驳回原因", "驳回申请", {
      confirmButtonText: "驳回",
      cancelButtonText: "取消",
      inputPlaceholder: "简要说明",
      inputValidator: (v) => {
        if (!String(v || "").trim()) return "请填写驳回原因";
        return true;
      }
    });
    reason = String(value || "").trim();
  } catch {
    return;
  }
  const res = rejectCatalogRequest(row.id, reason);
  if (!res.ok) {
    ElMessage.error(res.message);
    return;
  }
  ElMessage.success(res.message);
  bumpLocal();
}

const foCreateVisible = ref(false);
const foCreateFormRef = ref(null);
const foCreateForm = ref({ label: "", description: "" });
const foCreateRules = {
  label: [{ required: true, message: "请输入拟新增的数据字段名称", trigger: "blur" }]
};

function openFoCreateRequest() {
  foCreateForm.value = { label: "", description: "" };
  foCreateVisible.value = true;
}

function resetFoCreate() {
  foCreateFormRef.value?.clearValidate?.();
}

async function submitFoCreateRequest() {
  const form = foCreateFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  submitCatalogRequest({
    type: "create",
    proposedLabel: foCreateForm.value.label,
    proposedDescription: foCreateForm.value.description,
    requestedBy: me.value?.username || ""
  });
  foCreateVisible.value = false;
  ElMessage.success("已提交新增申请（模拟），请等待数据安全侧审核。");
  bumpLocal();
}

async function submitDeleteRequest(row) {
  try {
    await ElMessageBox.confirm(`确定提交删除「${row.label}」的申请吗？`, "申请删除", {
      type: "warning",
      confirmButtonText: "提交申请",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  submitCatalogRequest({
    type: "delete",
    catalogEntryId: row.id,
    proposedLabel: "",
    proposedDescription: "",
    requestedBy: me.value?.username || ""
  });
  ElMessage.success("已提交删除申请（模拟）。");
  bumpLocal();
}

function onCatalogPersist() {
  bumpLocal();
}

const loadMe = async () => {
  try {
    const { data } = await api.get("/api/v1/users/me");
    me.value = data;
  } catch {
    /* 未登录由全局守卫处理 */
  }
};

onMounted(() => {
  loadMe();
  window.addEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onCatalogPersist);
});

onBeforeUnmount(() => {
  window.removeEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onCatalogPersist);
});
</script>

<style scoped>
.fcp {
  padding: 24px 28px 32px;
}

.fcp__header {
  margin-bottom: 20px;
}

.fcp__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.fcp__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.fcp__code {
  padding: 1px 6px;
  font-size: 0.8125rem;
  border-radius: 4px;
  background: var(--dsms-fill-light, #f5f7fa);
  color: var(--dsms-text);
}

.fcp__toolbar {
  margin: 12px 0;
}

.fcp__table {
  width: 100%;
}

.fcp__card {
  margin-top: 20px;
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.fcp__card-title {
  font-weight: 600;
  color: var(--dsms-text);
}
</style>