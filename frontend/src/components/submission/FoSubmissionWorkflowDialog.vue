<template>
  <el-dialog
    :model-value="visible"
    class="fsw"
    :title="dialogTitle"
    width="960px"
    destroy-on-close
    append-to-body
    @update:model-value="emit('update:visible', $event)"
    @closed="onClosed"
  >
    <div v-if="task" class="fsw__body">
      <dl class="fsw__meta">
        <dt>任务名称</dt>
        <dd>{{ task.title }}</dd>
        <dt>业务功能</dt>
        <dd>{{ functionName(task.functionId) }}</dd>
        <dt>填报说明</dt>
        <dd>{{ task.dispatchNote || "—" }}</dd>
      </dl>

      <!-- 步骤 1：相关性 -->
      <template v-if="step === 'relevance'">
        <p class="fsw__lead">请先完成<strong>相关性判断问卷</strong>填报；提交后将按已配置表达式自动判定是否与数据安全相关。</p>
        <fo-lifecycle-fill-table
          v-if="relevanceColumns.length"
          v-model="relevanceRows"
          :columns="relevanceColumns"
          :bound-function-ids="[task.functionId]"
          :function-name="functionName"
        />
        <el-empty v-else description="请先在「功能数据安全相关性」中配置问卷题目" :image-size="64" />

        <el-alert
          v-if="relevancePreview"
          class="fsw__preview"
          :type="relevancePreview.code === 'relevant' ? 'warning' : 'success'"
          :closable="false"
          show-icon
          :title="`试算结论：${relevancePreview.text}`"
        >
          <template #default>
            <p class="fsw__preview-detail">表达式：{{ relevancePreview.expressionText }}</p>
          </template>
        </el-alert>
      </template>

      <!-- 步骤 2：生命周期 -->
      <template v-else-if="step === 'lifecycle'">
        <p class="fsw__lead">
          相关性判定为<strong>相关</strong>，请继续填写<strong>生命周期字段</strong>明细表；提交后系统将识别分类分级与安全要求并结束本任务。
        </p>
        <fo-lifecycle-fill-table
          v-model="lifecycleRows"
          :columns="lifecycleColumns"
          :bound-function-ids="[task.functionId]"
          :function-name="functionName"
        />
      </template>

      <!-- 步骤 3：规则识别结果 -->
      <template v-else-if="step === 'result'">
        <el-alert type="success" :closable="false" show-icon :title="governanceResult?.summaryMessage || '已完成识别'" />
        <el-table
          v-if="governanceResult?.fields?.length"
          class="fsw__gov-table"
          :data="governanceResult.fields"
          border
          stripe
          size="small"
        >
          <el-table-column prop="fieldLabel" label="数据字段" min-width="160" show-overflow-tooltip />
          <el-table-column prop="gradeLabel" label="密级" width="100" />
          <el-table-column prop="taxPath" label="分类" min-width="140" show-overflow-tooltip />
          <el-table-column label="触发的安全要求" min-width="200">
            <template #default="{ row }">
              <template v-if="row.triggeredRules?.length">
                <p v-for="(tr, i) in row.triggeredRules" :key="i" class="fsw__rule-line">
                  {{ tr.ruleName }}：{{ tr.actionPreview }}
                </p>
              </template>
              <span v-else class="fsw__muted">未命中</span>
            </template>
          </el-table-column>
        </el-table>
        <p class="fsw__result-note">任务已结束，填报内容与识别结果可在列表中「查看填报内容」（只读，不可修改）。</p>
      </template>
    </div>

    <template #footer>
      <el-button @click="emit('update:visible', false)">{{ step === 'result' ? '关闭' : '取消' }}</el-button>
      <template v-if="step === 'relevance'">
        <el-button @click="onPreviewRelevance">试算相关性</el-button>
        <el-button @click="onSaveRelevanceDraft">暂存</el-button>
        <el-button type="primary" @click="onSubmitRelevance">提交相关性判定</el-button>
      </template>
      <template v-else-if="step === 'lifecycle'">
        <el-button @click="onSaveLifecycleDraft">暂存</el-button>
        <el-button type="primary" @click="onSubmitLifecycle">提交并完成</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import FoLifecycleFillTable from "../FoLifecycleFillTable.vue";
import { getOrderedLifecycleFieldsForFoTable } from "../../data/lifecycleFieldConfigMock.js";
import { submissionFunctionName } from "../../data/submissionTasksMock.js";
import {
  advanceTaskToLifecycle,
  buildEmptyRelevanceRowForTask,
  buildRelevanceColumnsForTaskFunction,
  completeTaskAsIrrelevant,
  completeTaskAsRelevantSubmitted,
  evaluateRelevanceForFillRow,
  FO_RELEVANCE_IRRELEVANT,
  FO_RELEVANCE_RELEVANT,
  FO_WORKFLOW_STEP_LIFECYCLE,
  FO_WORKFLOW_STEP_RELEVANCE,
  saveTaskLifecycleDraft,
  saveTaskRelevanceDraft
} from "../../data/submissionFoWorkflowMock.js";

const props = defineProps({
  visible: { type: Boolean, default: false },
  task: { type: Object, default: null }
});

const emit = defineEmits(["update:visible", "saved"]);

const step = ref("relevance");
const relevanceRows = ref([]);
const lifecycleRows = ref([]);
const relevancePreview = ref(null);
const governanceResult = ref(null);

const relevanceColumns = computed(() =>
  props.task ? buildRelevanceColumnsForTaskFunction(props.task.functionId) : []
);

const lifecycleColumns = computed(() =>
  getOrderedLifecycleFieldsForFoTable().map((c) => ({
    field_key: c.field_key,
    label: c.label,
    input_type: c.input_type,
    required: c.required,
    help_text: c.help_text,
    max_length: c.max_length,
    allowed_values: Array.isArray(c.allowed_values) ? [...c.allowed_values] : []
  }))
);

const dialogTitle = computed(() => {
  if (step.value === "lifecycle") return "生命周期字段填报";
  if (step.value === "result") return "分类分级与安全要求识别结果";
  return "相关性判断填报";
});

function functionName(id) {
  return submissionFunctionName(id);
}

function initFromTask() {
  const t = props.task;
  if (!t) return;
  governanceResult.value = t.foGovernanceResult || null;
  if (t.foWorkflowStep === FO_WORKFLOW_STEP_LIFECYCLE && t.foFillStatus === "draft") {
    step.value = "lifecycle";
    lifecycleRows.value = Array.isArray(t.foFillLifecycleRows)
      ? JSON.parse(JSON.stringify(t.foFillLifecycleRows))
      : [];
    return;
  }
  step.value = "relevance";
  relevancePreview.value = null;
  const base = t.foRelevanceFillRow || buildEmptyRelevanceRowForTask(t.functionId);
  relevanceRows.value = [buildEmptyRelevanceRowForTask(t.functionId, base)];
  if (t.foFillLifecycleRows?.length) {
    lifecycleRows.value = JSON.parse(JSON.stringify(t.foFillLifecycleRows));
  } else {
    const cols = lifecycleColumns.value;
    const empty = {};
    for (const c of cols) empty[c.field_key] = "";
    empty.business_function = t.functionId;
    lifecycleRows.value = [empty];
  }
}

watch(
  () => [props.visible, props.task?.id],
  () => {
    if (props.visible && props.task) initFromTask();
  },
  { immediate: true }
);

function onClosed() {
  relevancePreview.value = null;
  governanceResult.value = null;
}

function currentRelevanceRow() {
  return relevanceRows.value[0] || buildEmptyRelevanceRowForTask(props.task.functionId);
}

function onPreviewRelevance() {
  const res = evaluateRelevanceForFillRow(currentRelevanceRow());
  if (!res.ok) {
    ElMessage.error(res.message);
    relevancePreview.value = null;
    return;
  }
  relevancePreview.value = res.conclusion;
}

async function onSubmitRelevance() {
  const row = currentRelevanceRow();
  const res = evaluateRelevanceForFillRow(row);
  if (!res.ok) {
    ElMessage.error(res.message);
    return;
  }
  const conclusion = res.conclusion;
  if (conclusion.code === FO_RELEVANCE_IRRELEVANT) {
    try {
      await ElMessageBox.confirm(
        `判定为「${conclusion.text}」。系统将保存填报记录，并为该业务功能打上「数据安全不相关」标签，本任务结束。是否继续？`,
        "确认提交",
        { type: "info", confirmButtonText: "确认", cancelButtonText: "取消" }
      );
    } catch {
      return;
    }
    completeTaskAsIrrelevant(props.task, row, conclusion);
    emit("saved", props.task);
    emit("update:visible", false);
    ElMessage.success("已提交：业务功能已标记为数据安全不相关，任务已结束。");
    return;
  }
  if (conclusion.code === FO_RELEVANCE_RELEVANT) {
    advanceTaskToLifecycle(props.task, row, conclusion);
    if (!lifecycleRows.value.length) {
      const cols = lifecycleColumns.value;
      const empty = {};
      for (const c of cols) empty[c.field_key] = "";
      empty.business_function = props.task.functionId;
      lifecycleRows.value = [empty];
    }
    step.value = "lifecycle";
    emit("saved", props.task);
    ElMessage.success("相关性判定为相关，请继续填写生命周期字段。");
  }
}

function onSaveRelevanceDraft() {
  const row = currentRelevanceRow();
  const res = evaluateRelevanceForFillRow(row);
  saveTaskRelevanceDraft(props.task, row, res.ok ? res.conclusion : null);
  emit("saved", props.task);
  ElMessage.success("已暂存相关性填报草稿。");
}

function validateLifecycleRows(rows) {
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
      if (c.field_key === "business_function") {
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

function onSaveLifecycleDraft() {
  saveTaskLifecycleDraft(props.task, lifecycleRows.value);
  emit("saved", props.task);
  ElMessage.success("已暂存生命周期填报草稿。");
}

async function onSubmitLifecycle() {
  if (!validateLifecycleRows(lifecycleRows.value)) return;
  const now = new Date().toISOString().slice(0, 16).replace("T", " ");
  const snap = buildLifecycleFormSnapshot(lifecycleRows.value, now);
  const { governance } = await completeTaskAsRelevantSubmitted(props.task, lifecycleRows.value, snap);
  governanceResult.value = governance;
  step.value = "result";
  emit("saved", props.task);
  ElMessage.success("已提交：分类分级与安全要求识别完成，任务已结束。");
}
</script>

<style scoped>
.fsw__body {
  min-height: 120px;
}

.fsw__meta {
  display: grid;
  grid-template-columns: 6rem 1fr;
  gap: 6px 12px;
  margin: 0 0 16px;
  font-size: 0.875rem;
}

.fsw__meta dt {
  margin: 0;
  color: var(--dsms-text-secondary);
}

.fsw__meta dd {
  margin: 0;
  color: var(--dsms-text);
}

.fsw__lead {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.fsw__preview {
  margin-top: 12px;
}

.fsw__preview-detail {
  margin: 4px 0 0;
  font-size: 0.8125rem;
}

.fsw__gov-table {
  margin-top: 16px;
  width: 100%;
}

.fsw__rule-line {
  margin: 0 0 4px;
  font-size: 0.8125rem;
  line-height: 1.45;
}

.fsw__muted {
  color: var(--dsms-text-secondary);
  font-size: 0.8125rem;
}

.fsw__result-note {
  margin: 16px 0 0;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}
</style>
