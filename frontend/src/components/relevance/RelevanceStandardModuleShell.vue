<template>
  <header class="rss-module__banner dsms-glass-panel" aria-labelledby="rss-module-title">
      <div class="rss-module__banner-head">
        <div>
          <h2 id="rss-module-title" class="rss-module__title">功能数据安全相关性</h2>
          <p class="rss-module__desc">
            配置业务功能与数据安全的相关性判定：<strong>相关性问卷</strong> →
            <strong>表达式配置和验证</strong>（问题×答案谓词 + 逻辑组合）。通过下方步骤切换，仅下方内容区刷新。
          </p>
        </div>
        <p class="rss-module__status" aria-live="polite">{{ statusSummary }}</p>
      </div>

      <nav class="rss-module__steps" aria-label="功能数据安全相关性配置步骤">
        <ol class="rss-module__step-list">
          <li v-for="(step, idx) in steps" :key="step.key" class="rss-module__step-item">
            <button
              type="button"
              class="rss-module__step-btn"
              :class="{
                'rss-module__step-btn--active': idx === activeStepIndex,
                'rss-module__step-btn--done': idx < activeStepIndex
              }"
              :aria-current="idx === activeStepIndex ? 'step' : undefined"
              @click="goStep(step)"
            >
              <span class="rss-module__step-num">{{ idx + 1 }}</span>
              <span class="rss-module__step-text">
                <span class="rss-module__step-title">{{ step.title }}</span>
                <span class="rss-module__step-desc">{{ step.description }}</span>
              </span>
            </button>
            <span v-if="idx < steps.length - 1" class="rss-module__step-sep" aria-hidden="true">›</span>
          </li>
        </ol>
      </nav>

      <el-alert
        v-for="(hint, i) in moduleHints"
        :key="i"
        class="rss-module__hint"
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
import { useRelevanceStandardModule } from "../../composables/useRelevanceStandardModule.js";

const props = defineProps({
  /** @type {'questionnaire' | 'expression'} */
  activePage: {
    type: String,
    required: true,
    validator: (v) => v === "questionnaire" || v === "expression"
  }
});

const route = useRoute();
const router = useRouter();
const { activeStepIndex, moduleHints, statusSummary, steps } = useRelevanceStandardModule(
  toRef(props, "activePage")
);

function goStep(step) {
  if (!step?.routeName || route.name === step.routeName) return;
  router.push({ name: step.routeName });
}
</script>

<style scoped>
.rss-module__banner {
  padding: 20px 24px 16px;
}

.rss-module__banner-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 24px;
  margin-bottom: 16px;
}

.rss-module__title {
  margin: 0 0 6px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.rss-module__desc {
  margin: 0;
  max-width: 52rem;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.rss-module__status {
  margin: 0;
  flex: 0 0 auto;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.rss-module__step-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rss-module__step-item {
  display: flex;
  align-items: center;
}

.rss-module__step-btn {
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

.rss-module__step-btn:hover {
  background: var(--dsms-fill-light, rgba(0, 0, 0, 0.04));
  color: var(--dsms-text);
}

.rss-module__step-btn--active {
  border-color: var(--el-color-primary-light-5, #c5d0e0);
  background: var(--el-color-primary-light-9, #f0f4f8);
  color: var(--dsms-text);
}

.rss-module__step-btn--done .rss-module__step-num {
  background: var(--el-color-primary);
  color: #fff;
}

.rss-module__step-num {
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

.rss-module__step-btn--active .rss-module__step-num {
  background: var(--el-color-primary);
  color: #fff;
}

.rss-module__step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rss-module__step-title {
  font-size: 0.875rem;
  font-weight: 600;
}

.rss-module__step-desc {
  font-size: 0.75rem;
  opacity: 0.85;
}

.rss-module__step-sep {
  margin: 0 4px;
  font-size: 1rem;
  color: var(--dsms-text-secondary);
  opacity: 0.5;
}

.rss-module__hint {
  margin-top: 12px;
}

.rss-module__hint + .rss-module__hint {
  margin-top: 8px;
}

@media (max-width: 720px) {
  .rss-module__step-sep {
    display: none;
  }

  .rss-module__step-item {
    flex: 1 1 100%;
  }
}
</style>
