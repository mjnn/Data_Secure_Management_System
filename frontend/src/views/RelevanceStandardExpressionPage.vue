<template>
  <section class="rse dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="rse-title">
    <header class="rse__header">
      <h3 id="rse-title" class="rse__title">表达式配置和验证</h3>
      <p class="rse__lead">
        配置<strong>问题 × 答案</strong>谓词及且/或逻辑，并映射相关/不相关结论；下方以<strong>功能 FO 填报表</strong>试填，
        提交后按表达式自动反馈<strong>功能数据安全相关性</strong>判定结果。
      </p>
    </header>

    <el-card class="rse__card" shadow="never">
      <template #header>
        <span class="rse__card-title">表达式配置</span>
      </template>

      <p v-if="!hasQuestions" class="rse__hint">
        请先在步骤 1「相关性问卷」中配置题目与选项，再返回本页配置表达式。
      </p>

      <RelevanceLogicExprBuilder v-else :group="expr.logic_root" />

      <div class="rse__conclusion">
        <span class="rse__conclusion-label">表达式为真时结论</span>
        <el-radio-group v-model="expr.conclusionWhenTrue">
          <el-radio v-for="c in conclusionOptions" :key="c.value" :value="c.value">{{ c.label }}</el-radio>
        </el-radio-group>
      </div>
      <div class="rse__conclusion">
        <span class="rse__conclusion-label">表达式为假时结论</span>
        <el-radio-group v-model="expr.conclusionWhenFalse">
          <el-radio v-for="c in conclusionOptions" :key="c.value" :value="c.value">{{ c.label }}</el-radio>
        </el-radio-group>
      </div>

      <p v-if="expressionPreview" class="rse__preview">
        <strong>预览：</strong>{{ expressionPreview }}
      </p>

      <div class="rse__actions">
        <el-button type="primary" :disabled="!hasQuestions" @click="onSave">保存表达式</el-button>
      </div>
    </el-card>

    <RelevanceFoFillEvaluateCard :expression="expr" />
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import RelevanceFoFillEvaluateCard from "../components/relevance/RelevanceFoFillEvaluateCard.vue";
import RelevanceLogicExprBuilder from "../components/relevance/RelevanceLogicExprBuilder.vue";
import {
  formatExpressionDisplay,
  hasRelevanceQuestionnaireForExpression,
  loadRelevanceExpression,
  RELEVANCE_CONCLUSION_OPTIONS,
  validateExpressionPayload
} from "../data/relevanceExpressionMock.js";
import { ensurePortalTenantReady, usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { fetchRelevanceExpression, saveRelevanceExpression } from "../api/dsmsSpaceApi.js";
import { PORTAL_DATA_REFRESH_EVENT } from "../api/portalApi.js";

const { tenantId, spaceId, ready } = usePortalTenantContext();

const refreshTick = ref(0);
const conclusionOptions = RELEVANCE_CONCLUSION_OPTIONS;

const expr = reactive(loadRelevanceExpression());

const hasQuestions = computed(() => {
  void refreshTick.value;
  return hasRelevanceQuestionnaireForExpression();
});

const expressionPreview = computed(() => {
  void refreshTick.value;
  return formatExpressionDisplay(expr);
});

function bumpLocal() {
  refreshTick.value++;
}

async function reloadExpressionFromApi() {
  if (!ready.value || !tenantId.value) return;
  try {
    const loaded = await fetchRelevanceExpression(tenantId.value, spaceId.value);
    expr.logic_root = loaded.logic_root;
    expr.conclusionWhenTrue = loaded.conclusionWhenTrue;
    expr.conclusionWhenFalse = loaded.conclusionWhenFalse;
    expr.updatedAt = loaded.updatedAt;
  } catch (e) {
    const loaded = loadRelevanceExpression();
    expr.logic_root = loaded.logic_root;
    expr.conclusionWhenTrue = loaded.conclusionWhenTrue;
    expr.conclusionWhenFalse = loaded.conclusionWhenFalse;
    expr.updatedAt = loaded.updatedAt;
    ElMessage.error(e.response?.data?.detail || "加载表达式失败");
  }
  bumpLocal();
}

async function onSave() {
  const check = validateExpressionPayload(expr);
  if (!check.ok) {
    ElMessage.error(check.message);
    return;
  }
  try {
    await saveRelevanceExpression(tenantId.value, spaceId.value, expr);
    ElMessage.success("已保存表达式");
    bumpLocal();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  }
}

onMounted(async () => {
  await ensurePortalTenantReady();
  await reloadExpressionFromApi();
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, reloadExpressionFromApi);
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, reloadExpressionFromApi);
});
</script>

<style scoped>
.rse {
  padding: 24px 28px 32px;
}

.rse__header {
  margin-bottom: 16px;
}

.rse__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.rse__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.rse__card {
  margin-bottom: 20px;
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.rse__card-title {
  font-weight: 600;
  color: var(--dsms-text);
}

.rse__hint {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.rse__conclusion {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin: 16px 0 12px;
}

.rse__conclusion-label {
  font-size: 0.875rem;
  color: var(--dsms-text-secondary);
}

.rse__preview {
  margin: 12px 0;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--dsms-text);
}

.rse__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
</style>
