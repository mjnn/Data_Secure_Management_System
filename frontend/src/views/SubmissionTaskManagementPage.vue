<template>
  <section class="stm dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="stm-title">
    <header class="stm__header dsms-animate-stagger-1">
      <h2 id="stm-title" class="stm__title">填报任务管理</h2>
      <p v-if="!me" class="stm__lead">正在加载当前用户…</p>
      <p v-else-if="isSecOrAdmin" class="stm__lead">
        数据安全 FO / 系统管理员：可<strong>多选业务功能</strong>，列表将汇总展示所选功能下的全部任务；支持<strong>跨功能多选草稿后批量下发</strong>（每条任务所属功能均须已绑定功能 FO）。可进入<strong>任务详情</strong>查看功能
        FO 填报情况并<strong>审核已提交</strong>的任务。当前为前端模拟数据。
      </p>
      <p v-else-if="isFunctionFo" class="stm__lead">
        功能 FO：此处列出<strong>已下发至您所绑定业务功能</strong>的填报任务。侧栏数字红点表示仍有<strong>未填报或草稿</strong>类待办。开始填报、暂存、提交等交互为<strong>壳层模拟</strong>；提交后可在「查看填报内容」中查看<strong>我的填报表单（只读）</strong>（依赖 `foFillFormSnapshot`，与数据安全侧详情一致，待流程定稿后由接口写入）。
      </p>
    </header>

    <!-- 数据安全 FO / 管理员 -->
    <template v-if="me && isSecOrAdmin">
      <div class="stm__toolbar dsms-animate-stagger-2">
        <el-form class="stm__filters" :inline="true" @submit.prevent>
          <el-form-item label="业务功能">
            <el-select
              v-model="selectedFunctionIds"
              multiple
              collapse-tags
              collapse-tags-tooltip
              filterable
              clearable
              placeholder="可多选，汇总展示任务"
              style="width: 400px"
              aria-label="选择业务功能（可多选）"
              @change="onFunctionsChange"
            >
              <el-option v-for="f in mockFunctions" :key="f.id" :label="functionOptionLabel(f)" :value="f.id" />
            </el-select>
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
    <template v-else-if="me && isFunctionFo">
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
            <el-select v-model="foSearchProgress" clearable placeholder="全部" style="width: 150px" aria-label="按填报进度筛选">
              <el-option label="全部" value="" />
              <el-option label="未填报" value="not_started" />
              <el-option label="草稿" value="draft" />
              <el-option label="已提交" value="submitted" />
              <el-option label="取消申请中" value="cancel_pending" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button @click="resetFoTaskFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
      <p class="stm__fo-hint dsms-animate-stagger-2">
        当前模拟绑定功能：<strong>{{ mockFoBoundFunctionIds.join("、") }}</strong>（与侧栏红点计数一致，后续由接口返回绑定关系）。上方可<strong>搜索、筛选</strong>本人任务列表。
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
            <el-tag v-else :type="foProgressTagType(row)" size="small">{{ foProgressLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right" align="right">
          <template #default="{ row }">
            <template v-if="row.foCancellationRequested">
              <el-button link type="primary" size="small" @click="openFoViewDialog(row)">查看说明</el-button>
            </template>
            <template v-else-if="foFillState(row) === 'not_started'">
              <el-button link type="primary" size="small" @click="onFoStartFill(row)">开始填报</el-button>
              <el-button link type="warning" size="small" @click="openFoCancelDialog(row)">申请取消填报</el-button>
            </template>
            <template v-else-if="foFillState(row) === 'draft'">
              <el-button link type="primary" size="small" @click="onFoContinueFill(row)">继续填报</el-button>
              <el-button link type="primary" size="small" plain @click="onFoSaveDraft(row)">暂存</el-button>
              <el-button link type="primary" size="small" @click="onFoSubmitFill(row)">提交填报</el-button>
              <el-button link type="warning" size="small" @click="openFoCancelDialog(row)">申请取消填报</el-button>
            </template>
            <template v-else-if="foFillState(row) === 'submitted'">
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

    <!-- 功能 FO：生命周期明细表填报 -->
    <el-dialog
      v-model="foFillVisible"
      title="填报任务（明细表）"
      width="960px"
      destroy-on-close
      append-to-body
      class="stm__fo-fill-dialog"
      @closed="resetFoFillDialog"
    >
      <div v-if="foFillRow" class="stm__fo-fill">
        <p class="stm__fo-fill__lead">
          首列为<strong>数据字段</strong>，第二列为<strong>业务功能</strong>（已绑定多项时可搜索单选；仅一项时自动带出），其后为数据安全 FO 配置的动态列。可<strong>新增条目</strong>追加行，填毕请暂存或提交。
        </p>
        <dl class="stm__view-dl stm__fo-fill__meta">
          <dt>任务名称</dt>
          <dd>{{ foFillRow.title }}</dd>
          <dt>填报任务说明</dt>
          <dd>{{ foFillRow.dispatchNote || "—" }}</dd>
        </dl>
        <fo-lifecycle-fill-table
          v-model="foFillTableRows"
          :columns="foFillColumns"
          :bound-function-ids="mockFoBoundFunctionIds"
          :function-name="functionNameById"
        />
      </div>
      <template #footer>
        <el-button @click="foFillVisible = false">关闭</el-button>
        <el-button @click="onFoSaveDraftInDialog">暂存草稿</el-button>
        <el-button type="primary" @click="onFoSubmitFromDialog">提交填报</el-button>
      </template>
    </el-dialog>

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
        </dl>
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
          v-else-if="foFillState(foViewRow) === 'submitted' || foFillState(foViewRow) === 'draft'"
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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api";
import {
  hasRenderableFormSnapshot,
  loadSubmissionTasksMerged,
  MOCK_SUBMISSION_FUNCTIONS,
  normalizeSubmissionTask,
  submissionFunctionById,
  submissionFunctionName,
  submissionTaskRowHasBoundFo,
  SUBMISSION_TASKS_STORAGE_KEY
} from "../data/submissionTasksMock";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";
import { bumpSubmissionTaskPersistListeners, MOCK_FO_BOUND_FUNCTION_IDS } from "../composables/useSubmissionTaskFoReminderCount";
import SubmissionFillFormReadonly from "../components/SubmissionFillFormReadonly.vue";
import FoLifecycleFillTable from "../components/FoLifecycleFillTable.vue";
import {
  buildEmptyLifecycleFillRow,
  getOrderedLifecycleFieldsForFoTable,
  LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY
} from "../data/lifecycleFieldConfigMock.js";
import { DATA_FIELD_CATALOG_PERSIST_EVENT } from "../data/dataFieldCatalogMock.js";

const mockFunctions = MOCK_SUBMISSION_FUNCTIONS;

const mockFoBoundFunctionIds = MOCK_FO_BOUND_FUNCTION_IDS;

function functionOptionLabel(f) {
  return f.functionFoBound ? `${f.name}（已绑 FO）` : `${f.name}（未绑 FO）`;
}

function functionNameById(id) {
  return submissionFunctionById(id)?.name || id;
}

function functionMeta(id) {
  return submissionFunctionById(id);
}

function rowHasBoundFo(row) {
  return submissionTaskRowHasBoundFo(row);
}

function selectAllFunctions() {
  selectedFunctionIds.value = mockFunctions.map((f) => f.id);
}

function clearFunctionSelection() {
  selectedFunctionIds.value = [];
}

function goToTaskDetail(row) {
  router.push({ name: "dashboard-submission-task-detail", params: { taskId: String(row.id) } });
}

const router = useRouter();
const me = ref(null);
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

const foTasks = computed(() =>
  tasks.value
    .filter((t) => t.status === "dispatched" && mockFoBoundFunctionIds.includes(t.functionId))
    .sort((a, b) => b.id - a.id)
);

const foSearchKeyword = ref("");
const foSearchProgress = ref("");

const foTasksFiltered = computed(() => {
  let list = foTasks.value;
  const p = foSearchProgress.value;
  if (p) {
    list = list.filter((t) => foFillState(t) === p);
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

const foFillVisible = ref(false);
const foFillRow = ref(null);
const foFillTableRows = ref([]);
const catalogRefreshTick = ref(0);

function onDataFieldCatalogPersist() {
  catalogRefreshTick.value++;
}

const foFillColumns = computed(() => {
  void catalogRefreshTick.value;
  return getOrderedLifecycleFieldsForFoTable().map((c) => ({
    field_key: c.field_key,
    label: c.label,
    input_type: c.input_type,
    required: c.required,
    help_text: c.help_text,
    max_length: c.max_length,
    allowed_values: Array.isArray(c.allowed_values) ? [...c.allowed_values] : []
  }));
});

function openFoFillDialog(row) {
  foFillRow.value = row;
  if (Array.isArray(row.foFillLifecycleRows) && row.foFillLifecycleRows.length) {
    foFillTableRows.value = JSON.parse(JSON.stringify(row.foFillLifecycleRows));
  } else {
    const keys = foFillColumns.value.map((c) => c.field_key);
    foFillTableRows.value = [buildEmptyLifecycleFillRow(keys, foFillColumns.value)];
  }
  if (mockFoBoundFunctionIds.length === 1) {
    const fid = mockFoBoundFunctionIds[0];
    foFillTableRows.value = foFillTableRows.value.map((r) => ({ ...r, [LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY]: fid }));
  }
  foFillVisible.value = true;
}

function resetFoFillDialog() {
  foFillRow.value = null;
  foFillTableRows.value = [];
}

function validateFoFillLifecycleRows(rows) {
  const cols = getOrderedLifecycleFieldsForFoTable();
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    for (const col of cols) {
      if (!col.required) continue;
      const v = r[col.field_key];
      const empty =
        v == null || (typeof v === "string" && !String(v).trim()) || (Array.isArray(v) && !v.length);
      if (empty) {
        ElMessage.error(`第 ${i + 1} 行「${col.label}」为必填。`);
        return false;
      }
    }
  }
  return true;
}

function buildLifecycleFormSnapshot(tableRows, submittedAt) {
  const colMeta = getOrderedLifecycleFieldsForFoTable();
  const columns = colMeta.map((c) => ({ field_key: c.field_key, label: c.label }));
  const displayRows = tableRows.map((r) => {
    const display = {};
    for (const c of colMeta) {
      const v = r[c.field_key];
      let text;
      if (c.field_key === LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY) {
        text = submissionFunctionName(v) || String(v || "");
      } else if (c.input_type === "multi_select") {
        text = Array.isArray(v) ? v.join("、") : String(v || "");
      } else {
        text = v != null ? String(v) : "";
      }
      display[c.field_key] = text.length ? text : "—";
    }
    return display;
  });
  return {
    versionKey: "lifecycle-table@v1",
    submittedAt,
    formTable: { columns, rows: displayRows },
    sections: [
      {
        heading: "填报摘要",
        fields: [
          { label: "明细行数", value: `${tableRows.length} 条` },
          { label: "提交时间", value: submittedAt }
        ]
      }
    ]
  };
}

function onFoSaveDraftInDialog() {
  const row = foFillRow.value;
  if (!row) return;
  row.foFillStatus = "draft";
  row.foFillLifecycleRows = JSON.parse(JSON.stringify(foFillTableRows.value));
  persistTasks();
  ElMessage.success("已暂存草稿（模拟）：明细表已写入本地。");
}

function onFoSubmitFromDialog() {
  const row = foFillRow.value;
  if (!row) return;
  if (!validateFoFillLifecycleRows(foFillTableRows.value)) return;
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  row.foFillStatus = "submitted";
  row.foFillLifecycleRows = JSON.parse(JSON.stringify(foFillTableRows.value));
  row.foFillContentSummary = `已提交 ${foFillTableRows.value.length} 条明细（模拟）。`;
  row.foFillFormSnapshot = buildLifecycleFormSnapshot(foFillTableRows.value, now);
  persistTasks();
  foFillVisible.value = false;
  ElMessage.success("已提交填报（模拟）：可在「查看填报内容」中查看只读明细表。");
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
  return sel.every((r) => submissionTaskRowHasBoundFo(r));
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

const loadMe = async () => {
  try {
    const { data } = await api.get("/api/v1/users/me");
    me.value = data;
    const role = effectivePlatformRole(data);
    if (role !== PLATFORM_ROLE.SYSTEM_ADMIN && role !== PLATFORM_ROLE.SECURITY_FO && role !== PLATFORM_ROLE.FUNCTION_FO) {
      ElMessage.warning("当前角色无权访问填报任务管理。");
      await router.replace({ name: "dashboard-home" });
    }
  } catch {
    /* 未登录由全局守卫处理 */
  }
};

onMounted(() => {
  loadTasks();
  loadMe();
  window.addEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onDataFieldCatalogPersist);
});

onBeforeUnmount(() => {
  window.removeEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onDataFieldCatalogPersist);
});

let nextTaskId = 100;
function ensureNextId() {
  const max = tasks.value.reduce((m, t) => Math.max(m, t.id), 0);
  nextTaskId = Math.max(nextTaskId, max + 1);
}

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
    const today = new Date().toISOString().slice(0, 10);
    const fid = selectedFunctionIds.value[0];
    ensureNextId();
    tasks.value.push({
      id: nextTaskId++,
      functionId: fid,
      title: editForm.title.trim(),
      internalNote: editForm.internalNote.trim(),
      status: "draft",
      dispatchNote: null,
      dispatchedAt: null,
      createdAt: today
    });
    ElMessage.success("已创建（模拟）");
  } else {
    const row = tasks.value.find((t) => t.id === editingId.value);
    if (row) {
      row.title = editForm.title.trim();
      row.internalNote = editForm.internalNote.trim();
    }
    ElMessage.success("已保存（模拟）");
  }
  persistTasks();
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
  tasks.value = tasks.value.filter((t) => t.id !== row.id);
  persistTasks();
  ElMessage.success("已删除（模拟）");
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
  const unbound = targets.filter((r) => !submissionTaskRowHasBoundFo(r));
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
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  const targets = tasks.value.filter((t) => dispatchTargetIds.value.includes(t.id) && t.status === "draft");
  if (targets.some((t) => !submissionTaskRowHasBoundFo(t))) {
    ElMessage.error("选中任务中存在未绑定功能 FO 的业务功能，已中止下发。");
    return;
  }
  for (const t of targets) {
    t.status = "dispatched";
    t.dispatchNote = note;
    t.dispatchedAt = now;
    t.foFillStatus = "not_started";
    t.foCancellationRequested = false;
    t.foCancellationReason = "";
    t.foFillContentSummary = "";
    t.foFillFormSnapshot = null;
    t.foFillLifecycleRows = null;
    t.foExtraAssignees = undefined;
    t.auditStatus = null;
    t.auditComment = "";
    t.auditedAt = null;
  }
  persistTasks();
  dispatchVisible.value = false;
  selectedRows.value = [];
  tableRef.value?.clearSelection?.();
  ElMessage.success(`已下发 ${dispatchTargetIds.value.length} 条任务（模拟）`);
}

function foFillState(row) {
  if (row.foCancellationRequested) return "cancel_pending";
  return row.foFillStatus || "not_started";
}

function foProgressLabel(row) {
  const s = foFillState(row);
  if (s === "draft") return "草稿";
  if (s === "submitted") return "已提交";
  return "未填报";
}

function foProgressTagType(row) {
  const s = foFillState(row);
  if (s === "submitted") return "success";
  if (s === "draft") return "warning";
  return "info";
}

function onFoStartFill(row) {
  openFoFillDialog(row);
  row.foFillStatus = "draft";
  persistTasks();
}

function onFoContinueFill(row) {
  openFoFillDialog(row);
}

function onFoSaveDraft(row) {
  if (foFillVisible.value && foFillRow.value?.id === row.id) {
    onFoSaveDraftInDialog();
    return;
  }
  openFoFillDialog(row);
  nextTick(() => onFoSaveDraftInDialog());
}

function onFoSubmitFill(row) {
  if (!Array.isArray(row.foFillLifecycleRows) || !row.foFillLifecycleRows.length) {
    ElMessage.warning("请先点击「继续填报」打开明细表，填写后暂存或于弹窗内提交。");
    return;
  }
  if (!validateFoFillLifecycleRows(row.foFillLifecycleRows)) return;
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  row.foFillStatus = "submitted";
  row.foFillContentSummary = row.foFillContentSummary || `已提交 ${row.foFillLifecycleRows.length} 条明细（模拟）。`;
  row.foFillFormSnapshot = buildLifecycleFormSnapshot(row.foFillLifecycleRows, now);
  persistTasks();
  ElMessage.success("已提交填报（模拟）：可在「查看填报内容」中查看只读明细表。");
}

const foCancelVisible = ref(false);
const foCancelFormRef = ref(null);
const foCancelTargetId = ref(null);
const foCancelForm = reactive({ reason: "" });
const foCancelRules = {
  reason: [{ required: true, message: "请填写取消理由", trigger: "blur" }]
};

function openFoCancelDialog(row) {
  if (foFillState(row) === "submitted") return;
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
  row.foCancellationRequested = true;
  row.foCancellationReason = foCancelForm.reason.trim();
  persistTasks();
  foCancelVisible.value = false;
  ElMessage.success("已提交取消申请（模拟）。");
}

const foViewVisible = ref(false);
const foViewRow = ref(null);

const foViewDialogTitle = computed(() => {
  if (!foViewRow.value) return "查看";
  if (foFillState(foViewRow.value) === "submitted") return "查看填报内容";
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
