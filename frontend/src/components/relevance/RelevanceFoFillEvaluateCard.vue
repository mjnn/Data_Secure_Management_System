<template>
  <el-card class="rfe dsms-glass-panel" shadow="never">
    <template #header>
      <span class="rfe__title">功能 FO 填报与相关性判定</span>
    </template>

    <p class="rfe__hint">
      与功能 FO 在「填报任务管理」中填写<strong>相关性判定</strong>时使用的明细表一致：首列为<strong>业务功能</strong>，其后各列为问卷题目（单选）。
      填完后点击<strong>提交</strong>，系统按上方已保存的表达式自动判定该业务功能的<strong>数据安全相关性</strong>。
    </p>

    <p v-if="!foPreviewColumns.length" class="rfe__empty">请先在步骤 1「相关性问卷」中配置题目与选项。</p>
    <template v-else>
      <div class="rfe__table-wrap">
        <fo-lifecycle-fill-table
          v-model="fillRows"
          :columns="foPreviewColumns"
          :bound-function-ids="boundFunctionIds"
          :function-name="functionNameById"
        />
      </div>

      <div class="rfe__actions">
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交并判定相关性</el-button>
      </div>

      <el-alert
        v-if="submitResult"
        class="rfe__result"
        :type="submitResult.conclusionCode === 'relevant' ? 'success' : 'info'"
        :closable="false"
        show-icon
        :title="`功能数据安全相关性：${submitResult.conclusionText}`"
      >
        <template #default>
          <p class="rfe__result-detail">
            业务功能：<strong>{{ submittedFunctionLabel }}</strong>
          </p>
          <p class="rfe__result-detail">
            表达式求值：{{ submitResult.satisfied ? "成立" : "不成立" }} · {{ submitResult.expressionText }}
          </p>
        </template>
      </el-alert>
    </template>
  </el-card>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import FoLifecycleFillTable from "../FoLifecycleFillTable.vue";
import { fetchMyFoBindings } from "../../api/portalApi.js";
import { usePortalTenantContext } from "../../composables/usePortalTenantContext.js";
import { submissionFunctionById } from "../../data/submissionTasksMock.js";
import { buildEmptyLifecycleFillRow } from "../../data/lifecycleFieldConfigMock.js";
import { resolveConclusionFromFillRow } from "../../data/relevanceExpressionMock.js";
import {
  buildRelevanceQuestionnairePreviewColumns,
  loadRelevanceQuestionnaireQuestions,
  RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY,
  RELEVANCE_QUESTIONNAIRE_PERSIST_EVENT
} from "../../data/relevanceQuestionnaireMock.js";
import { RELEVANCE_EXPRESSION_PERSIST_EVENT } from "../../data/relevanceExpressionMock.js";

const props = defineProps({
  /** 当前表达式（含 logic_root 与结论映射） */
  expression: { type: Object, required: true }
});

const refreshTick = ref(0);
const fillRows = ref([]);
const submitting = ref(false);
const submitResult = ref(null);
const submittedFunctionLabel = ref("—");

const { tenantId, spaceId, ready } = usePortalTenantContext();
const boundFunctionIds = ref([]);

async function loadBindings() {
  if (!ready.value || !tenantId.value) return;
  try {
    const data = await fetchMyFoBindings(tenantId.value, spaceId.value);
    const keys = (data?.bindings || data?.items || [])
      .map((b) => b.function_key || b.business_function_key)
      .filter(Boolean);
    boundFunctionIds.value = keys.length ? keys : [];
  } catch {
    boundFunctionIds.value = [];
  }
  resetFillRows();
}

watch([ready, tenantId, spaceId], () => {
  if (ready.value) loadBindings();
});

const questionRows = computed(() => {
  void refreshTick.value;
  return loadRelevanceQuestionnaireQuestions();
});

const foPreviewColumns = computed(() => buildRelevanceQuestionnairePreviewColumns(questionRows.value));

const previewColumnFingerprint = computed(() =>
  foPreviewColumns.value
    .map((c) =>
      [
        c.field_key,
        c.input_type,
        String(c.required),
        (c.allowed_values || []).join("|"),
        String(c.max_length ?? "")
      ].join(":")
    )
    .join(";")
);

function functionNameById(id) {
  return submissionFunctionById(id)?.name || id;
}

function resetFillRows() {
  submitResult.value = null;
  submittedFunctionLabel.value = "—";
  const cols = foPreviewColumns.value;
  if (!cols.length) {
    fillRows.value = [];
    return;
  }
  const keys = cols.map((c) => c.field_key);
  let next = [buildEmptyLifecycleFillRow(keys, cols)];
  if (boundFunctionIds.value.length === 1) {
    const fid = boundFunctionIds.value[0];
    next = next.map((r) => ({ ...r, [RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY]: fid }));
  }
  fillRows.value = next;
}

watch(previewColumnFingerprint, resetFillRows, { immediate: true });

function bumpLocal() {
  refreshTick.value++;
}

function onSubmit() {
  const row = fillRows.value[0];
  if (!row) {
    ElMessage.error("请先填写问卷。");
    return;
  }
  submitting.value = true;
  try {
    const res = resolveConclusionFromFillRow(props.expression, row);
    if (!res.ok) {
      ElMessage.error(res.message);
      return;
    }
    submitResult.value = res.result;
    const fid = String(row[RELEVANCE_QUESTIONNAIRE_BUSINESS_FUNCTION_KEY] || "").trim();
    submittedFunctionLabel.value = fid ? functionNameById(fid) : "—";
    ElMessage.success(`判定完成：${res.result.conclusionText}`);
  } finally {
    submitting.value = false;
  }
}

function onPersist() {
  resetFillRows();
  bumpLocal();
}

onMounted(() => {
  window.addEventListener(RELEVANCE_QUESTIONNAIRE_PERSIST_EVENT, onPersist);
  window.addEventListener(RELEVANCE_EXPRESSION_PERSIST_EVENT, onPersist);
  if (ready.value) loadBindings();
});

onBeforeUnmount(() => {
  window.removeEventListener(RELEVANCE_QUESTIONNAIRE_PERSIST_EVENT, onPersist);
  window.removeEventListener(RELEVANCE_EXPRESSION_PERSIST_EVENT, onPersist);
});
</script>

<style scoped>
.rfe {
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.rfe__title {
  font-weight: 600;
  color: var(--dsms-text);
}

.rfe__hint {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.rfe__empty {
  margin: 0;
  font-size: 0.875rem;
  color: var(--dsms-text-secondary);
}

.rfe__table-wrap {
  width: 100%;
  overflow-x: auto;
}

.rfe__actions {
  margin-top: 16px;
}

.rfe__result {
  margin-top: 16px;
}

.rfe__result-detail {
  margin: 4px 0 0;
  font-size: 0.8125rem;
}
</style>
