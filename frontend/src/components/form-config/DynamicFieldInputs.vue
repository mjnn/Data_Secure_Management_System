<template>
  <el-row v-if="fields.length" :gutter="12">
    <el-col v-for="field in fields" :key="field.field_key" :span="field.input_type === 'textarea' ? 24 : 12">
      <el-form-item :label="field.label">
        <template #label>
          <span class="field-label-with-tip">
            {{ field.label }}
            <el-tooltip v-if="field.help_text" :content="field.help_text" placement="top">
              <el-icon><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <dsms-filterable-select
          v-if="field.input_type === 'single_select'"
          :model-value="getValue(field.field_key)"
          style="width: 100%"
          clearable
          @update:model-value="setTextValue(field.field_key, $event)"
        >
          <el-option
            v-for="option in getOptions(field.field_key)"
            :key="`${field.field_key}-${option}`"
            :label="option"
            :value="option"
          />
        </dsms-filterable-select>
        <dsms-filterable-select
          v-else-if="field.input_type === 'multi_select'"
          :model-value="getArrayValue(field.field_key)"
          style="width: 100%"
          multiple
          collapse-tags
          clearable
          @update:model-value="setArrayValue(field.field_key, $event)"
        >
          <el-option
            v-for="option in getOptions(field.field_key)"
            :key="`${field.field_key}-${option}`"
            :label="option"
            :value="option"
          />
        </dsms-filterable-select>
        <el-input
          v-else-if="field.input_type === 'textarea'"
          :model-value="getValue(field.field_key)"
          type="textarea"
          :rows="3"
          :maxlength="field.max_length || undefined"
          show-word-limit
          @update:model-value="setTextValue(field.field_key, $event)"
        />
        <el-input
          v-else
          :model-value="getValue(field.field_key)"
          :maxlength="field.max_length || undefined"
          @update:model-value="setTextValue(field.field_key, $event)"
        />
      </el-form-item>
    </el-col>
  </el-row>
</template>

<script setup>
import { QuestionFilled } from "@element-plus/icons-vue";
import DsmsFilterableSelect from "../DsmsFilterableSelect.vue";

const props = defineProps({
  fields: { type: Array, required: true },
  modelValue: { type: Object, required: true }
});

const emit = defineEmits(["update:modelValue"]);

const getOptions = (fieldKey) => {
  const field = props.fields.find((item) => item.field_key === fieldKey);
  return (field?.allowed_values || []).filter((item) => item.trim());
};

const getValue = (fieldKey) => {
  const value = props.modelValue[fieldKey];
  if (Array.isArray(value)) return value.join(", ");
  return String(value || "");
};

const getArrayValue = (fieldKey) => {
  const value = props.modelValue[fieldKey];
  if (Array.isArray(value)) return value.map((item) => String(item || "")).filter(Boolean);
  return [];
};

const setTextValue = (fieldKey, value) => {
  emit("update:modelValue", {
    ...props.modelValue,
    [fieldKey]: String(value || "")
  });
};

const setArrayValue = (fieldKey, value) => {
  const next = Array.isArray(value) ? value.map((item) => String(item || "")).filter(Boolean) : [];
  emit("update:modelValue", {
    ...props.modelValue,
    [fieldKey]: next
  });
};
</script>

<style scoped>
.field-label-with-tip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
