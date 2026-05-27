<template>
  <header class="txs-module__banner dsms-glass-panel" aria-labelledby="txs-module-title">
      <div class="txs-module__banner-head">
        <div>
          <h2 id="txs-module-title" class="txs-module__title">数据分类标准</h2>
          <p class="txs-module__desc">
            维护数据分类体系：<strong>分类树层级</strong> → <strong>分类树节点</strong> → <strong>数据字段分类</strong> → <strong>矩阵与规则</strong> → <strong>自动分类结果</strong>。通过下方步骤切换，仅下方内容区刷新。
          </p>
        </div>
        <p class="txs-module__status" aria-live="polite">{{ statusSummary }}</p>
      </div>

      <nav class="txs-module__steps" aria-label="数据分类标准配置步骤">
        <ol class="txs-module__step-list">
          <li v-for="(step, idx) in steps" :key="step.key" class="txs-module__step-item">
            <button
              type="button"
              class="txs-module__step-btn"
              :class="{
                'txs-module__step-btn--active': idx === activeStepIndex,
                'txs-module__step-btn--done': idx < activeStepIndex
              }"
              :aria-current="idx === activeStepIndex ? 'step' : undefined"
              @click="goStep(step)"
            >
              <span class="txs-module__step-num">{{ idx + 1 }}</span>
              <span class="txs-module__step-text">
                <span class="txs-module__step-title">{{ step.title }}</span>
                <span class="txs-module__step-desc">{{ step.description }}</span>
              </span>
            </button>
            <span v-if="idx < steps.length - 1" class="txs-module__step-sep" aria-hidden="true">›</span>
          </li>
        </ol>
      </nav>

      <el-alert
        v-for="(hint, i) in moduleHints"
        :key="i"
        class="txs-module__hint"
        :type="hint.type"
        :title="hint.title"
        :description="hint.description"
        :closable="false"
        show-icon
      />
  </header>
</template>

<script setup>
import { toRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useTaxonomyModule } from "../../composables/useTaxonomyModule.js";

const props = defineProps({
  /** @type {'levels' | 'nodes' | 'fieldClassification' | 'classificationConfig' | 'classificationResults'} */
  activePage: {
    type: String,
    required: true,
    validator: (v) =>
      v === "levels" ||
      v === "nodes" ||
      v === "fieldClassification" ||
      v === "classificationConfig" ||
      v === "classificationResults"
  }
});

const route = useRoute();
const router = useRouter();
const { activeStepIndex, moduleHints, statusSummary, steps } = useTaxonomyModule(toRef(props, "activePage"));

function goStep(step) {
  if (!step?.routeName || route.name === step.routeName) return;
  router.push({ name: step.routeName });
}
</script>

<style scoped>
.txs-module__banner {
  padding: 20px 24px 16px;
}

.txs-module__banner-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 24px;
  margin-bottom: 16px;
}

.txs-module__title {
  margin: 0 0 6px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.txs-module__desc {
  margin: 0;
  max-width: 52rem;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.txs-module__status {
  margin: 0;
  flex: 0 0 auto;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.txs-module__step-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.txs-module__step-item {
  display: flex;
  align-items: center;
}

.txs-module__step-btn {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 0;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  color: var(--dsms-text-secondary);
  transition:
    background-color var(--dsms-duration-short) var(--dsms-ease-standard),
    border-color var(--dsms-duration-short) var(--dsms-ease-standard),
    color var(--dsms-duration-short) var(--dsms-ease-standard);
}

.txs-module__step-btn:hover {
  background: var(--dsms-fill-light, rgba(0, 0, 0, 0.04));
  color: var(--dsms-text);
}

.txs-module__step-btn--active {
  border-color: var(--el-color-primary-light-5, #c5d0e0);
  background: var(--el-color-primary-light-9, #f0f4f8);
  color: var(--dsms-text);
}

.txs-module__step-btn--done .txs-module__step-num {
  background: var(--el-color-primary);
  color: #fff;
}

.txs-module__step-num {
  flex: 0 0 1.5rem;
  width: 1.5rem;
  height: 1.5rem;
  line-height: 1.5rem;
  text-align: center;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 50%;
  background: var(--dsms-fill-light, #e8ecf0);
  color: var(--dsms-text-secondary);
}

.txs-module__step-btn--active .txs-module__step-num {
  background: var(--el-color-primary);
  color: #fff;
}

.txs-module__step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.txs-module__step-title {
  font-size: 0.875rem;
  font-weight: 600;
}

.txs-module__step-desc {
  font-size: 0.75rem;
  opacity: 0.85;
}

.txs-module__step-sep {
  margin: 0 4px;
  font-size: 1rem;
  color: var(--dsms-text-secondary);
  opacity: 0.5;
}

.txs-module__hint {
  margin-top: 12px;
}

.txs-module__hint + .txs-module__hint {
  margin-top: 8px;
}

@media (max-width: 720px) {
  .txs-module__step-sep {
    display: none;
  }

  .txs-module__step-item {
    flex: 1 1 100%;
  }
}
</style>
