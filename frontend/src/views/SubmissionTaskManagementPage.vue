<template>
  <section class="stm dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="stm-title">
    <header class="stm__header dsms-animate-stagger-1">
      <h2 id="stm-title" class="stm__title">填报任务管理</h2>
      <p v-if="isSecOrAdmin" class="stm__lead">
        数据安全 FO / 系统管理员：可<strong>多选业务功能</strong>，列表将汇总展示所选功能下的全部任务；支持<strong>跨功能多选草稿后批量下发</strong>（每条任务所属功能均须已绑定功能 FO）。可进入<strong>任务详情</strong>查看功能
        FO 填报情况并<strong>审核已提交</strong>的任务。当前为前端模拟数据。
      </p>
      <p v-else-if="isFunctionFo" class="stm__lead">
        功能 FO：须先<strong>绑定至少一个业务功能</strong>，再处理已下发任务。流程为<strong>相关性判断填报</strong> →
        判定<strong>不相关</strong>则打标并结束；判定<strong>相关</strong>则继续<strong>生命周期字段填报</strong>，提交后系统识别分类分级与安全要求并结束任务。已结束任务仅可<strong>查看（只读）</strong>。
      </p>
    </header>

    <!-- 数据安全 FO / 管理员 -->
    <template v-if="meReady && isSecOrAdmin">
      <div class="stm__toolbar dsms-animate-stagger-2">
        <el-form class="stm__filters" :inline="true" @submit.prevent>
          <el-form-item label="业务功能">
            <dsms-filterable-select
              v-model="selectedFunctionIds"
              multiple
              collapse-tags
              collapse-tags-tooltip
              clearable
              placeholder="搜索业务功能，可多选"
              style="width: 400px"
              aria-label="选择业务功能（可多选）"
              @change="onFunctionsChange"
            >
              <el-option v-for="f in mockFunctions" :key="f.id" :label="functionOptionLabel(f)" :value="f.id" />
            </dsms-filterable-select>
          </el-form-item>
          <el-form-item>
            <el-button link type="primary" @click="selectAllFunctions">全选功能</el-button>
            <el-button link type="primary" @click="clearFunctionSelection">清空</el-button>
          </el-form-item>
          <el-form-item v-if="selectedFunctionIds.length">
            <el-tag
              v-for="fid in selectedFunctionIds"
              :key="fid"
              :type="functionMeta(fid)?.functionFoBound ? 'success' : 'warning'"
              size="small"
              class="stm__fn-tag"
            >
              {{ functionNameById(fid) }}：{{ functionMeta(fid)?.functionFoBound ? "已绑 FO" : "未绑 FO" }}
            </el-tag>
          </el-form-item>
        </el-form>
        <div class="stm__actions">
          <el-button type="primary" :disabled="selectedFunctionIds.length !== 1" @click="openCreateDialog">
            新建任务
          </el-button>
          <el-button type="primary" plain :disabled="!canBatchDispatch" @click="openDispatchDialog(null)">
            批量下发
          </el-button>
        </div>
      </div>

      <el-alert
        v-if="!selectedFunctionIds.length"
        type="info"
        :closable="false"
        show-icon
        class="stm__alert"
        title="请先选择至少一个业务功能"
        description="多选后列表将汇总展示；新建任务时请先只保留一个所选功能。批量下发支持跨所选功能多选草稿行，但每条任务所属功能须已绑定功能 FO。"
      />

      <el-table
        v-else
        ref="tableRef"
        class="stm__table"
        :data="tasksForFunction"
        row-key="id"
        border
        stripe
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="48" :selectable="rowSelectable" />
        <el-table-column label="业务功能" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ functionNameById(row.functionId) }}
          </template>
        </el-table-column>
        <el-table-column prop="title" label="任务名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="internalNote" label="备注" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.internalNote || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'dispatched' ? 'success' : 'info'" size="small">
              {{ row.status === "dispatched" ? "已下发" : "草稿" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="填报任务说明（下发时）" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.dispatchNote || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="dispatchedAt" label="下发时间" width="120">
          <template #default="{ row }">
            {{ row.dispatchedAt || "—" }}
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="120" />
        <el-table-column label="操作" width="260" fixed="right" align="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goToTaskDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" :disabled="row.status !== 'draft'" @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-button
              link
              type="primary"
              size="small"
              :disabled="row.status !== 'draft' || !rowHasBoundFo(row)"
              @click="openDispatchDialog([row])"
            >
              下发
            </el-button>
            <el-button link type="danger" size="small" :disabled="row.status !== 'draft'" @click="onDeleteTask(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- 功能 FO -->
    <template v-else-if="meReady && isFunctionFo">
      <fo-business-function-binding-card class="dsms-animate-stagger-2" @updated="onFoBindingUpdated" />

      <div class="stm__fo-toolbar dsms-animate-stagger-2">
        <el-form class="stm__fo-filters" :inline="true" @submit.prevent>
          <el-form-item label="关键词">
            <el-input
              v-model="foSearchKeyword"
              clearable
              placeholder="任务名称、填报说明、业务功能、摘要…"
              style="width: 260px"
              aria-label="搜索我的填报任务"
            />
          </el-form-item>
          <el-form-item label="我的进度">
            <dsms-filterable-select
              v-model="foSearchProgress"
              clearable
              placeholder="搜索进度"
              style="width: 150px"
              aria-label="按填报进度筛选"
            >
              <el-option label="全部" value="" />
              <el-option label="未填报" value="not_started" />
              <el-option label="相关性填报中" value="relevance_draft" />
              <el-option label="生命周期填报中" value="lifecycle_draft" />
              <el-option label="已提交（相关）" value="submitted" />
              <el-option label="已结束（不相关）" value="completed_irrelevant" />
              <el-option label="取消申请中" value="cancel_pending" />
              <el-option label="已取消" value="cancelled" />
            </dsms-filterable-select>
          </el-form-item>
          <el-form-item>
            <el-button @click="resetFoTaskFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      <el-alert
        v-if="!foBoundFunctionIds.length"
        class="stm__alert dsms-animate-stagger-2"
        type="warning"
        :closable="false"
        show-icon
        title="请先绑定业务功能"
        description="在上方卡片中保存至少一项业务功能绑定后，方可开始填报。"
      />
      <p v-else class="stm__fo-hint dsms-animate-stagger-2">
        当前已绑定功能：<strong>{{ foBoundFunctionLabels }}</strong>。可<strong>搜索、筛选</strong>本人任务列表。
      </p>
      <el-table
        class="stm__table"
        :data="foTasksFiltered"
        row-key="id"
        border
        stripe
        :empty-text="foTableEmptyText"
      >
        <el-table-column prop="title" label="任务名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="业务功能" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ functionNameById(row.functionId) }}
          </template>
        </el-table-column>
        <el-table-column label="填报任务说明" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.dispatchNote || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="dispatchedAt" label="下发时间" width="150" />
        <el-table-column label="我的进度" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.foCancellationRequested" type="warning" size="small">取消申请中</el-tag>
            <el-tag v-else :type="foWorkflowProgressTagType(row)" size="small">{{ foWorkflowProgressLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right" align="right">
          <template #default="{ row }">
            <template v-if="foWorkflowProgressKey(row) === 'cancel_pending'">
              <el-button link type="primary" size="small" @click="openFoViewDialog(row)">查看申请</el-button>
            </template>
            <template v-else-if="foWorkflowProgressKey(row) === 'cancelled'">
              <el-button link type="primary" size="small" @click="openFoViewDialog(row)">查看说明</el-button>
            </template>
            <template v-else-if="foCanFill(row) && foWorkflowProgressKey(row) === 'not_started'">
              <el-button link type="primary" size="small" @click="onFoStartFill(row)">开始填报</el-button>
              <el-button link type="warning" size="small" @click="openFoCancelDialog(row)">申请取消填报</el-button>
            </template>
            <template v-else-if="foCanFill(row) && (foWorkflowProgressKey(row) === 'relevance_draft' || foWorkflowProgressKey(row) === 'lifecycle_draft')">
              <el-button link type="primary" size="small" @click="onFoContinueFill(row)">继续填报</el-button>
              <el-button link type="warning" size="small" @click="openFoCancelDialog(row)">申请取消填报</el-button>
            </template>
            <template v-else-if="foWorkflowProgressKey(row) === 'submitted' || foWorkflowProgressKey(row) === 'completed_irrelevant'">
              <el-button link type="primary" size="small" @click="openFoViewDialog(row)">查看填报内容</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- 新建 / 编辑（管理员侧） -->
    <el-dialog
      v-model="editVisible"
      :title="editMode === 'create' ? '新建填报任务' : '编辑填报任务'"
      width="480px"
      destroy-on-close
      append-to-body
      @closed="resetEditForm"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top">
        <el-form-item label="任务名称" prop="title">
          <el-input v-model="editForm.title" maxlength="80" show-word-limit />
        </el-form-item>
        <el-form-item label="备注（可选）" prop="internalNote">
          <el-input v-model="editForm.internalNote" type="textarea" :rows="2" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 下发（管理员侧） -->
    <el-dialog
      v-model="dispatchVisible"
      title="下发填报任务"
      width="520px"
      destroy-on-close
      append-to-body
      @closed="resetDispatchForm"
    >
      <p class="stm__dialog-p">
        将下发 <strong>{{ dispatchTargetIds.length }}</strong> 条草稿任务（可来自多个已选业务功能）；每条任务所属功能须已绑定功能 FO。须填写对执行人的<strong>填报任务说明</strong>（必填）。
      </p>
      <el-form ref="dispatchFormRef" :model="dispatchForm" :rules="dispatchRules" label-position="top">
        <el-form-item label="填报任务说明" prop="note">
          <el-input
            v-model="dispatchForm.note"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            placeholder="请说明本次下发的填报要求、截止要求、注意事项等"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dispatchVisible = false">取消</el-button>
        <el-button type="primary" @click="submitDispatch">确认下发</el-button>
      </template>
    </el-dialog>

    <!-- 功能 FO：申请取消（理由必填） -->
    <el-dialog
      v-model="foCancelVisible"
      title="申请取消填报"
      width="480px"
      destroy-on-close
      append-to-body
      @closed="resetFoCancelForm"
    >
      <p class="stm__dialog-p">提交后进入「取消申请中」状态（模拟）；取消理由对审批方可见，请如实填写。</p>
      <el-form ref="foCancelFormRef" :model="foCancelForm" :rules="foCancelRules" label-position="top">
        <el-form-item label="取消理由" prop="reason">
          <el-input
            v-model="foCancelForm.reason"
            type="textarea"
            :rows="4"
            maxlength="1000"
            show-word-limit
            placeholder="请说明申请取消的原因（必填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="foCancelVisible = false">关闭</el-button>
        <el-button type="primary" @click="submitFoCancel">提交申请</el-button>
      </template>
    </el-dialog>

    <fo-submission-workflow-dialog
      v-model:visible="foWorkflowVisible"
      :task="foWorkflowTask"
      @saved="onFoWorkflowSaved"
    />

    <!-- 功能 FO：查看说明 / 查看填报表单（只读） -->
    <el-dialog
      v-model="foViewVisible"
      :title="foViewDialogTitle"
      width="640px"
      destroy-on-close
      append-to-body
    >
      <div v-if="foViewRow" class="stm__fo-view">
        <dl class="stm__view-dl">
          <dt>任务名称</dt>
          <dd>{{ foViewRow.title }}</dd>
          <dt>填报任务说明</dt>
          <dd>{{ foViewRow.dispatchNote || "—" }}</dd>
          <template v-if="foViewRow.foCancellationRequested">
            <dt>取消理由</dt>
            <dd>{{ foViewRow.foCancellationReason || "—" }}</dd>
          </template>
          <dt>填报摘要</dt>
          <dd>{{ foViewRow.foFillContentSummary || "—" }}</dd>
          <template v-if="foViewRow.foRelevanceConclusion">
            <dt>相关性结论</dt>
            <dd>{{ foViewRow.foRelevanceConclusion === "irrelevant" ? "数据安全不相关" : "相关" }}</dd>
          </template>
        </dl>
        <template v-if="foViewRow.foGovernanceResult?.fields?.length">
          <h3 class="stm__fo-view__h3">分类分级与安全要求（只读）</h3>
          <el-table :data="foViewRow.foGovernanceResult.fields" border stripe size="small" class="stm__gov-table">
            <el-table-column prop="fieldLabel" label="数据字段" min-width="140" show-overflow-tooltip />
            <el-table-column prop="gradeLabel" label="密级" width="88" />
            <el-table-column prop="taxPath" label="分类" min-width="120" show-overflow-tooltip />
            <el-table-column label="安全要求" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="!row.triggeredRules?.length">未命中</span>
                <span v-else>{{ row.triggeredRules.map((t) => t.ruleName).join("；") }}</span>
              </template>
            </el-table-column>
          </el-table>
        </template>
        <template v-if="hasRenderableFormSnapshot(foViewRow.foFillFormSnapshot)">
          <h3 class="stm__fo-view__h3">我的填报表单（只读）</h3>
          <SubmissionFillFormReadonly :snapshot="foViewRow.foFillFormSnapshot" />
        </template>
        <el-alert
          v-else-if="foFillState(foViewRow) === 'cancel_pending'"
          class="stm__fo-view-alert"
          type="warning"
          :closable="false"
          show-icon
          title="暂无完整表单快照"
          description="取消申请处理中；若曾保存过结构化快照，审批结束后可在任务更新中再次查看。"
        />
        <el-alert
          v-else-if="foWorkflowProgressKey(foViewRow) === 'submitted' || foWorkflowProgressKey(foViewRow) === 'relevance_draft' || foWorkflowProgressKey(foViewRow) === 'lifecycle_draft'"
          class="stm__fo-view-alert"
          type="info"
          :closable="false"
          show-icon
          title="暂无结构化表单快照"
          description="填报流程与接口定稿后，将在此展示与您填报时一致的只读表单。已提交时系统会持久化 fo_fill_form_snapshot；若刚提交仍看不到，请刷新页面。"
        />
      </div>
      <template #footer>
        <el-button type="primary" @click="foViewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import {
  hasRenderableFormSnapshot,
  normalizeSubmissionTask,
  submissionFunctionById
} from "../data/submissionTasksMock";
import { ensurePortalTenantReady, usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import {
  createSubmissionTask,
  dispatchSubmissionTasks,
  fetchBusinessFunctions,
  fetchMyFoBindings,
  fetchSubmissionTasks,
  patchSubmissionTask,
  PORTAL_DATA_REFRESH_EVENT,
  requestSubmissionCancel
} from "../api/portalApi.js";
import { setPortalSyncContext } from "../api/portalTaskSync.js";
import { isFunctionMarkedIrrelevant } from "../data/foFunctionSecurityTagMock.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";
import {
  bumpSubmissionTaskPersistListeners
} from "../composables/useSubmissionTaskFoReminderCount";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import SubmissionFillFormReadonly from "../components/SubmissionFillFormReadonly.vue";
import FoBusinessFunctionBindingCard from "../components/submission/FoBusinessFunctionBindingCard.vue";
import FoSubmissionWorkflowDialog from "../components/submission/FoSubmissionWorkflowDialog.vue";
import { foWorkflowProgressKey,
  foWorkflowProgressLabel,
  foWorkflowProgressTagType
} from "../data/submissionFoWorkflowMock.js";

const { tenantId, spaceId, ready } = usePortalTenantContext();
const mockFunctions = ref([]);
const functionCatalog = ref([]);

function rebuildFunctionCatalog() {
  functionCatalog.value = mockFunctions.value;
}

function submissionFunctionByIdLocal(id) {
  return mockFunctions.value.find((f) => f.id === id) || submissionFunctionById(id);
}

function functionNameById(id) {
  return submissionFunctionByIdLocal(id)?.name || id;
}

function functionMeta(id) {
  return submissionFunctionByIdLocal(id);
}

const foBoundFunctionIds = ref([]);

const foBoundFunctionLabels = computed(() =>
  foBoundFunctionIds.value.map((id) => functionNameById(id)).join("、")
);

function onFoBindingUpdated(ids) {
  foBoundFunctionIds.value = [...ids];
  bumpSubmissionTaskPersistListeners();
}

function foCanFill(row) {
  return foBoundFunctionIds.value.length > 0 && foBoundFunctionIds.value.includes(row.functionId);
}

function rowHasBoundFo(row) {
  const fn = submissionFunctionByIdLocal(row.functionId);
  return !!(fn?.functionFoBound);
}

function functionOptionLabel(f) {
  return f.functionFoBound ? `${f.name}（已绑 FO）` : `${f.name}（未绑 FO）`;
}

function selectAllFunctions() {
  selectedFunctionIds.value = mockFunctions.value.map((f) => f.id);
}

function clearFunctionSelection() {
  selectedFunctionIds.value = [];
}

function goToTaskDetail(row) {
  router.push({ name: "dashboard-submission-task-detail", params: { taskId: String(row.id) } });
}

const router = useRouter();
const { user: me, ready: meReady, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();
const selectedFunctionIds = ref([]);
const tasks = ref([]);
const selectedRows = ref([]);
const tableRef = ref(null);

const platformRole = computed(() => effectivePlatformRole(me.value));
const isSecOrAdmin = computed(
  () => platformRole.value === PLATFORM_ROLE.SYSTEM_ADMIN || platformRole.value === PLATFORM_ROLE.SECURITY_FO
);
const isFunctionFo = computed(() => platformRole.value === PLATFORM_ROLE.FUNCTION_FO);

const tasksForFunction = computed(() =>
  tasks.value
    .filter((t) => selectedFunctionIds.value.includes(t.functionId))
    .sort((a, b) => b.id - a.id)
);

const foTasks = computed(() => {
  const bound = foBoundFunctionIds.value;
  return tasks.value
    .filter((t) => t.status === "dispatched" && bound.includes(t.functionId))
    .sort((a, b) => b.id - a.id);
});

const foSearchKeyword = ref("");
const foSearchProgress = ref("");

const foTasksFiltered = computed(() => {
  let list = foTasks.value;
  const p = foSearchProgress.value;
  if (p) {
    list = list.filter((t) => foWorkflowProgressKey(t) === p);
  }
  const q = foSearchKeyword.value.trim().toLowerCase();
  if (q) {
    list = list.filter((t) => {
      const parts = [
        t.title,
        t.dispatchNote,
        functionNameById(t.functionId),
        t.foFillContentSummary,
        t.internalNote,
        t.dispatchedAt
      ]
        .filter((x) => x != null && String(x).length)
        .join(" ")
        .toLowerCase();
      return parts.includes(q);
    });
  }
  return list;
});

const foTableEmptyText = computed(() => {
  if (!foTasks.value.length) return "暂无下发给您的填报任务";
  return "无匹配任务，请调整关键词或进度筛选";
});

const foWorkflowVisible = ref(false);
const foWorkflowTask = ref(null);

function openFoWorkflow(row) {
  if (!foCanFill(row)) {
    ElMessage.warning("请先在上方绑定至少一个业务功能。");
    return;
  }
  if (isFunctionMarkedIrrelevant(row.functionId) && foWorkflowProgressKey(row) === "not_started") {
    ElMessage.info("该业务功能已标记为数据安全不相关；若有新任务请按下发说明处理。");
  }
  foWorkflowTask.value = row;
  foWorkflowVisible.value = true;
}

function onFoWorkflowSaved() {
  persistTasks();
}

function resetFoTaskFilters() {
  foSearchKeyword.value = "";
  foSearchProgress.value = "";
}

const canBatchDispatch = computed(() => {
  if (!selectedFunctionIds.value.length) return false;
  const sel = selectedRows.value;
  if (!sel.length) return false;
  if (!sel.every((r) => r.status === "draft")) return false;
  return sel.every((r) => rowHasBoundFo(r));
});

function rowSelectable(row) {
  return row.status === "draft";
}

function onFunctionsChange() {
  selectedRows.value = [];
  tableRef.value?.clearSelection?.();
}

function onSelectionChange(rows) {
  selectedRows.value = rows;
}

function normalizeTask(t) {
  return normalizeSubmissionTask(t);
}

async function loadTasks() {
  if (!ready.value || !tenantId.value) return;
  try {
    const list = await fetchSubmissionTasks(tenantId.value, spaceId.value);
    tasks.value = list.map((t) => normalizeSubmissionTask(t));
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载任务失败");
  }
}

async function loadFunctionsAndBindings() {
  if (!ready.value || !tenantId.value) return;
  try {
    mockFunctions.value = await fetchBusinessFunctions(tenantId.value, spaceId.value);
    rebuildFunctionCatalog();
    const binding = await fetchMyFoBindings(tenantId.value, spaceId.value);
    foBoundFunctionIds.value = binding.function_keys || [];
    setPortalSyncContext(tenantId.value, spaceId.value);
  } catch {
    foBoundFunctionIds.value = [];
  }
}

function persistTasks() {
  loadTasks();
  bumpSubmissionTaskPersistListeners();
}

function onPortalDataRefresh() {
  loadFunctionsAndBindings();
  loadTasks();
}

onMounted(async () => {
  await Promise.all([ensureCurrentUser(), ensurePortalTenantReady()]);
  const role = effectivePlatformRole(me.value);
  if (
    role !== PLATFORM_ROLE.SYSTEM_ADMIN &&
    role !== PLATFORM_ROLE.SECURITY_FO &&
    role !== PLATFORM_ROLE.FUNCTION_FO
  ) {
    ElMessage.warning("当前角色无权访问填报任务管理。");
    await router.replace({ name: "dashboard-home" });
    return;
  }
  loadFunctionsAndBindings();
  loadTasks();
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onPortalDataRefresh);
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onPortalDataRefresh);
});

const editVisible = ref(false);
const editMode = ref("create");
const editFormRef = ref(null);
const editingId = ref(null);
const editForm = reactive({
  title: "",
  internalNote: ""
});

const editRules = {
  title: [{ required: true, message: "请输入任务名称", trigger: "blur" }]
};

function openCreateDialog() {
  if (selectedFunctionIds.value.length !== 1) {
    ElMessage.warning("新建任务时请在业务功能中只选择一项；或先清空再单选。");
    return;
  }
  editMode.value = "create";
  editingId.value = null;
  editForm.title = "";
  editForm.internalNote = "";
  editVisible.value = true;
}

function openEditDialog(row) {
  editMode.value = "edit";
  editingId.value = row.id;
  editForm.title = row.title;
  editForm.internalNote = row.internalNote || "";
  editVisible.value = true;
}

function resetEditForm() {
  editingId.value = null;
  editFormRef.value?.clearValidate?.();
}

async function submitEdit() {
  const form = editFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  if (editMode.value === "create") {
    if (!selectedFunctionIds.value.length || selectedFunctionIds.value.length !== 1) return;
    const fid = selectedFunctionIds.value[0];
    try {
      await createSubmissionTask(tenantId.value, spaceId.value, {
        function_key: fid,
        title: editForm.title.trim(),
        internal_note: editForm.internalNote.trim()
      });
      ElMessage.success("已创建任务");
      await loadTasks();
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || "创建失败");
      return;
    }
  } else {
    try {
      await patchSubmissionTask(tenantId.value, spaceId.value, editingId.value, {
        title: editForm.title.trim(),
        internalNote: editForm.internalNote.trim()
      });
      ElMessage.success("已保存");
      await loadTasks();
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || "保存失败");
      return;
    }
  }
  editVisible.value = false;
}

async function onDeleteTask(row) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${row.title}」？`, "删除任务", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  ElMessage.info("后端暂未提供删除接口，草稿任务请通过审批流作废或联系管理员。");
}

const dispatchVisible = ref(false);
const dispatchFormRef = ref(null);
const dispatchTargetIds = ref([]);
const dispatchForm = reactive({ note: "" });

const dispatchRules = {
  note: [{ required: true, message: "请填写填报任务说明", trigger: "blur" }]
};

function openDispatchDialog(rows) {
  let targets = [];
  if (rows && rows.length) {
    targets = rows.filter((r) => r.status === "draft");
  } else {
    targets = selectedRows.value.filter((r) => r.status === "draft");
  }
  const unbound = targets.filter((r) => !rowHasBoundFo(r));
  if (unbound.length) {
    const names = [...new Set(unbound.map((u) => functionNameById(u.functionId)))];
    ElMessage.warning(`所选草稿中含未绑定功能 FO 的业务功能，不能下发：${names.join("、")}`);
    return;
  }
  if (!targets.length) {
    ElMessage.warning("请选择至少一条草稿任务，或使用表格多选后批量下发。");
    return;
  }
  dispatchTargetIds.value = targets.map((t) => t.id);
  dispatchForm.note = "";
  dispatchVisible.value = true;
}

function resetDispatchForm() {
  dispatchTargetIds.value = [];
  dispatchFormRef.value?.clearValidate?.();
}

async function submitDispatch() {
  const form = dispatchFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  const note = dispatchForm.note.trim();
  const targets = tasks.value.filter((t) => dispatchTargetIds.value.includes(t.id) && t.status === "draft");
  if (targets.some((t) => !rowHasBoundFo(t))) {
    ElMessage.error("选中任务中存在未绑定功能 FO 的业务功能，已中止下发。");
    return;
  }
  try {
    const data = await dispatchSubmissionTasks(
      tenantId.value,
      spaceId.value,
      dispatchTargetIds.value,
      note
    );
    ElMessage.success(data.message || `已下发 ${dispatchTargetIds.value.length} 条任务`);
    await loadTasks();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "下发失败");
    return;
  }

  dispatchVisible.value = false;
  selectedRows.value = [];
  tableRef.value?.clearSelection?.();
}

function foFillState(row) {
  return foWorkflowProgressKey(row);
}

function onFoStartFill(row) {
  openFoWorkflow(row);
}

function onFoContinueFill(row) {
  openFoWorkflow(row);
}

const foCancelVisible = ref(false);
const foCancelFormRef = ref(null);
const foCancelTargetId = ref(null);
const foCancelForm = reactive({ reason: "" });
const foCancelRules = {
  reason: [{ required: true, message: "请填写取消理由", trigger: "blur" }]
};

function openFoCancelDialog(row) {
  const k = foWorkflowProgressKey(row);
  if (k === "submitted" || k === "completed_irrelevant") return;
  foCancelTargetId.value = row.id;
  foCancelForm.reason = "";
  foCancelVisible.value = true;
}

function resetFoCancelForm() {
  foCancelTargetId.value = null;
  foCancelFormRef.value?.clearValidate?.();
}

async function submitFoCancel() {
  const form = foCancelFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  const id = foCancelTargetId.value;
  const row = tasks.value.find((t) => t.id === id);
  if (!row) return;
  try {
    const data = await requestSubmissionCancel(tenantId.value, spaceId.value, id, foCancelForm.reason.trim());
    await loadTasks();
    foCancelVisible.value = false;
    ElMessage.success(data.message || "已提交取消申请");
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "提交失败");
  }
}

const foViewVisible = ref(false);
const foViewRow = ref(null);

const foViewDialogTitle = computed(() => {
  if (!foViewRow.value) return "查看";
  const k = foWorkflowProgressKey(foViewRow.value);
  if (k === "submitted" || k === "completed_irrelevant") return "查看填报内容（只读）";
  return "任务说明";
});

function openFoViewDialog(row) {
  foViewRow.value = row;
  foViewVisible.value = true;
}
</script>

<style scoped>
.stm {
  padding: 24px 28px 32px;
}

.stm__header {
  margin-bottom: 20px;
}

.stm__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.stm__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.stm__fo-hint {
  margin: 0 0 16px;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.stm__fo-toolbar {
  margin-bottom: 12px;
}

.stm__fo-filters {
  flex: 1;
  min-width: 0;
}

.stm__fo-filters :deep(.el-form-item) {
  margin-bottom: 8px;
}

.stm__toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.stm__filters {
  flex: 1;
  min-width: 0;
}

.stm__filters :deep(.el-form-item) {
  margin-bottom: 8px;
}

.stm__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
}

.stm__alert {
  margin-bottom: 16px;
}

.stm__table {
  width: 100%;
}

.stm__dialog-p {
  margin: 0 0 12px;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.stm__view-dl {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
}

.stm__view-dl dt {
  margin-top: 12px;
  font-weight: 600;
  color: var(--dsms-text);
}

.stm__view-dl dt:first-child {
  margin-top: 0;
}

.stm__view-dl dd {
  margin: 4px 0 0;
  color: var(--dsms-text-secondary);
}

.stm__fn-tag {
  margin-right: 6px;
  margin-bottom: 4px;
}

.stm__fo-view {
  max-height: min(70vh, 520px);
  overflow-y: auto;
}

.stm__fo-view__h3 {
  margin: 16px 0 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.stm__fo-view-alert {
  margin-top: 12px;
}

.stm__gov-table {
  width: 100%;
  margin-bottom: 12px;
}

.stm__fo-fill__lead {
  margin: 0 0 12px;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.stm__fo-fill__meta {
  margin-bottom: 16px;
}
</style>
