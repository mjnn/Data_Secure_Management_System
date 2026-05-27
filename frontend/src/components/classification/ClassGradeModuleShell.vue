<template>
  <header class="cgm__banner dsms-glass-panel" aria-labelledby="cgm-module-title">
    <div class="cgm__banner-head">
      <div>
        <h2 id="cgm-module-title" class="cgm__title">密级绑定</h2>
        <p class="cgm__desc">
          维护空间内<strong>密级定义</strong>，并为<strong>数据字段主表</strong>条目绑定
          <code class="cgm__code">grade_label</code>（联调对齐 <code class="cgm__code">fields/class-grade</code>）。通过下方步骤切换，仅下方内容区刷新。
        </p>
      </div>
      <p class="cgm__status" aria-live="polite">{{ statusSummary }}</p>
    </div>

    <nav class="cgm__steps" aria-label="密级绑定配置步骤">
      <ol class="cgm__step-list">
        <li v-for="(step, idx) in steps" :key="step.key" class="cgm__step-item">
          <button
            type="button"
            class="cgm__step-btn"
            :class="{
              'cgm__step-btn--active': idx === activeStepIndex,
              'cgm__step-btn--done': idx < activeStepIndex
            }"
            :aria-current="idx === activeStepIndex ? 'step' : undefined"
            @click="goStep(step)"
          >
            <span class="cgm__step-num">{{ idx + 1 }}</span>
            <span class="cgm__step-text">
              <span class="cgm__step-title">{{ step.title }}</span>
              <span class="cgm__step-desc">{{ step.description }}</span>
            </span>
          </button>
          <span v-if="idx < steps.length - 1" class="cgm__step-sep" aria-hidden="true">›</span>
        </li>
      </ol>
    </nav>

    <el-alert
      v-for="(hint, i) in moduleHints"
      :key="i"
      class="cgm__hint"
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
import { useClassGradeModule } from "../../composables/useClassGradeModule.js";

const props = defineProps({
  /** @type {'levels' | 'bindings'} */
  activePage: {
    type: String,
    required: true,
    validator: (v) => v === "levels" || v === "bindings"
  }
});

const route = useRoute();
const router = useRouter();
const { activeStepIndex, moduleHints, statusSummary, steps } = useClassGradeModule(toRef(props, "activePage"));

function goStep(step) {
  if (!step?.routeName || route.name === step.routeName) return;
  router.push({ name: step.routeName });
}
</script>

<style scoped>
.cgm__banner {
  padding: 20px 24px 16px;
}

.cgm__banner-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 24px;
  margin-bottom: 16px;
}

.cgm__title {
  margin: 0 0 6px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.cgm__desc {
  margin: 0;
  max-width: 52rem;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.cgm__code {
  font-size: 0.8125rem;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--dsms-page-bg, #f4f6f9);
}

.cgm__status {
  margin: 0;
  flex: 0 0 auto;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.cgm__step-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 0;
  margin: 0;
  padding: 0;
  list-style: none;
}

.cgm__step-item {
  display: flex;
  align-items: center;
}

.cgm__step-btn {
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

.cgm__step-btn:hover {
  background: var(--dsms-fill-light, rgba(0, 0, 0, 0.04));
  color: var(--dsms-text);
}

.cgm__step-btn--active {
  border-color: var(--el-color-primary-light-5, #c5d0e0);
  background: var(--el-color-primary-light-9, #f0f4f8);
  color: var(--dsms-text);
}

.cgm__step-btn--done .cgm__step-num {
  background: var(--el-color-primary);
  color: #fff;
}

.cgm__step-num {
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

.cgm__step-btn--active .cgm__step-num {
  background: var(--el-color-primary);
  color: #fff;
}

.cgm__step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cgm__step-title {
  font-size: 0.875rem;
  font-weight: 600;
}

.cgm__step-desc {
  font-size: 0.75rem;
  opacity: 0.85;
}

.cgm__step-sep {
  margin: 0 4px;
  font-size: 1rem;
  color: var(--dsms-text-secondary);
  opacity: 0.5;
}

.cgm__hint {
  margin-top: 12px;
}

.cgm__hint + .cgm__hint {
  margin-top: 8px;
}

@media (max-width: 720px) {
  .cgm__step-sep {
    display: none;
  }

  .cgm__step-item {
    flex: 1 1 100%;
  }
}
</style>
