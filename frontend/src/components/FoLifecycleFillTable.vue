<template>
  <div class="flft">
    <el-table :data="modelValue" border stripe size="small" class="flft__table" empty-text="暂无行，请点击新增条目">
      <el-table-column type="index" label="#" width="48" align="center" />
      <el-table-column
        v-for="col in columns"
        :key="col.field_key"
        :min-width="columnMinWidth(col)"
      >
        <template #header>
          <span class="flft__th">
            {{ col.label }}
            <el-tooltip v-if="col.help_text" :content="col.help_text" placement="top">
              <el-icon class="flft__tip"><QuestionFilled /></el-icon>
            </el-tooltip>
            <span v-if="col.required" class="flft__req" aria-hidden="true">*</span>
          </span>
        </template>
        <template #default="{ row, $index }">
          <template v-if="col.field_key === businessFunctionKey">
            <template v-if="boundFunctionIds.length <= 1">
              <span class="flft__readonly">{{ boundFunctionLabelSingle }}</span>
            </template>
            <el-select
              v-else
              :model-value="row[col.field_key]"
              class="flft__cell-select"
              filterable
              clearable
              placeholder="搜索并选择业务功能"
              @update:model-value="patchRow($index, col.field_key, $event)"
            >
              <el-option v-for="fid in boundFunctionIds" :key="fid" :label="functionName(fid)" :value="fid" />
            </el-select>
          </template>
          <template v-else-if="col.field_key === dataFieldKey">
            <el-select
              :model-value="row[col.field_key]"
              class="flft__cell-select"
              filterable
              clearable
              placeholder="搜索并选择数据字段"
              @update:model-value="patchRow($index, col.field_key, $event)"
            >
              <el-option v-for="opt in dataFieldOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </template>
          <template v-else-if="col.input_type === 'single_select'">
            <el-select
              :model-value="row[col.field_key]"
              class="flft__cell-select"
              filterable
              clearable
              placeholder="请选择"
              @update:model-value="patchRow($index, col.field_key, $event)"
            >
              <el-option v-for="opt in col.allowed_values || []" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </template>
          <template v-else-if="col.input_type === 'multi_select'">
            <el-select
              :model-value="row[col.field_key] || []"
              class="flft__cell-select"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              clearable
              placeholder="请选择"
              @update:model-value="patchRow($index, col.field_key, $event)"
            >
              <el-option v-for="opt in col.allowed_values || []" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </template>
          <template v-else-if="col.input_type === 'textarea'">
            <el-input
              :model-value="row[col.field_key]"
              type="textarea"
              :rows="2"
              :maxlength="col.max_length || undefined"
              show-word-limit
              @update:model-value="patchRow($index, col.field_key, $event)"
            />
          </template>
          <template v-else>
            <el-input :model-value="row[col.field_key]" @update:model-value="patchRow($index, col.field_key, $event)" />
          </template>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="72" align="center" fixed="right">
        <template #default="{ $index }">
          <el-button link type="danger" size="small" :disabled="modelValue.length <= 1" @click="removeRow($index)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="flft__actions">
      <el-button type="primary" plain size="small" @click="addRow">新增条目</el-button>
    </div>
  </div>
</template>

<script setup>
import { QuestionFilled } from "@element-plus/icons-vue";
import { computed } from "vue";
import {
  buildEmptyLifecycleFillRow,
  LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY,
  LIFECYCLE_BUILTIN_DATA_FIELD_KEY
} from "../data/lifecycleFieldConfigMock.js";

const props = defineProps({
  columns: { type: Array, required: true },
  modelValue: { type: Array, required: true },
  boundFunctionIds: { type: Array, required: true },
  functionName: { type: Function, required: true }
});

const emit = defineEmits(["update:modelValue"]);

const dataFieldKey = LIFECYCLE_BUILTIN_DATA_FIELD_KEY;
const businessFunctionKey = LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY;

const dataFieldOptions = computed(() => {
  const col = props.columns.find((c) => c.field_key === dataFieldKey);
  return (col?.allowed_values || []).filter(Boolean);
});

const boundFunctionLabelSingle = computed(() => {
  const id = props.boundFunctionIds[0];
  return id ? props.functionName(id) : "—";
});

function columnMinWidth(col) {
  if (col.input_type === "textarea") return 200;
  if (col.input_type === "multi_select") return 200;
  if (col.field_key === businessFunctionKey || col.field_key === dataFieldKey) return 200;
  return 140;
}

function patchRow(index, key, value) {
  const next = props.modelValue.map((r, i) => (i === index ? { ...r, [key]: value } : { ...r }));
  emit("update:modelValue", next);
}

function addRow() {
  const keys = props.columns.map((c) => c.field_key);
  const empty = buildEmptyLifecycleFillRow(keys, props.columns);
  let next = [...props.modelValue, empty];
  if (props.boundFunctionIds.length === 1) {
    const fid = props.boundFunctionIds[0];
    next = next.map((r, i) => (i === next.length - 1 ? { ...r, [businessFunctionKey]: fid } : r));
  }
  emit("update:modelValue", next);
}

function removeRow(index) {
  if (props.modelValue.length <= 1) return;
  const next = props.modelValue.filter((_, i) => i !== index);
  emit("update:modelValue", next);
}
</script>

<style scoped>
.flft__table {
  width: 100%;
}

.flft__th {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.flft__tip {
  color: var(--dsms-text-secondary);
  cursor: help;
}

.flft__req {
  color: var(--el-color-danger);
  font-weight: 600;
}

.flft__cell-select {
  width: 100%;
}

.flft__readonly {
  font-size: 0.875rem;
  color: var(--dsms-text-secondary);
}

.flft__actions {
  margin-top: 10px;
}
</style>
