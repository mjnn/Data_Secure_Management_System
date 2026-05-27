<template>
  <div class="dsms-richtext">
    <div class="dsms-richtext__toolbar" role="toolbar" aria-label="富文本格式">
      <el-button size="small" text type="primary" title="加粗" @click="exec('bold')">B</el-button>
      <el-button size="small" text type="primary" title="斜体" @click="exec('italic')"><em>I</em></el-button>
      <el-button size="small" text type="primary" title="无序列表" @click="exec('insertUnorderedList')">• 列表</el-button>
    </div>
    <div
      ref="bodyRef"
      class="dsms-richtext__body"
      contenteditable="true"
      role="textbox"
      aria-multiline="true"
      :data-placeholder="placeholder"
      @input="onInput"
      @blur="onInput"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  placeholder: { type: String, default: "请输入安全要求说明（暂为前端富文本占位，联调格式待定）" }
});

const emit = defineEmits(["update:modelValue"]);

const bodyRef = ref(null);

function onInput() {
  emit("update:modelValue", bodyRef.value?.innerHTML ?? "");
}

function exec(cmd) {
  document.execCommand(cmd, false);
  bodyRef.value?.focus();
  onInput();
}

function syncFromModel(html) {
  const el = bodyRef.value;
  if (!el) return;
  const next = html || "";
  if (el.innerHTML !== next) el.innerHTML = next;
}

watch(
  () => props.modelValue,
  (v) => syncFromModel(v),
  { immediate: false }
);

onMounted(() => syncFromModel(props.modelValue));
</script>

<style scoped>
.dsms-richtext {
  width: 100%;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 8px;
  background: var(--el-fill-color-blank, #fff);
  overflow: hidden;
}

.dsms-richtext__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--el-border-color-lighter, #ebeef5);
  background: var(--dsms-page-bg, #f8f9fb);
}

.dsms-richtext__body {
  min-height: 160px;
  max-height: 320px;
  overflow-y: auto;
  padding: 12px 14px;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--dsms-text);
  outline: none;
}

.dsms-richtext__body:empty::before {
  content: attr(data-placeholder);
  color: var(--dsms-text-secondary);
  pointer-events: none;
}

.dsms-richtext__body :deep(ul) {
  margin: 0.5em 0;
  padding-left: 1.25em;
}
</style>
