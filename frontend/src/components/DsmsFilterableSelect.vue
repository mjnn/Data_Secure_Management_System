<script setup>
/**
 * 全站统一：单选/多选下拉均支持模糊搜索（Element Plus filterable）。
 * 用法与 el-select 一致，通过默认插槽传入 el-option。
 */
defineOptions({ inheritAttrs: false });

defineProps({
  modelValue: { type: [String, Number, Boolean, Array, Object], default: undefined },
  placeholder: { type: String, default: "请选择" },
  clearable: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  multiple: { type: Boolean, default: false }
});

const emit = defineEmits(["update:modelValue", "change"]);
</script>

<template>
  <el-select
    class="dsms-filterable-select"
    :model-value="modelValue"
    filterable
    :placeholder="placeholder"
    :clearable="clearable"
    :disabled="disabled"
    :multiple="multiple"
    v-bind="$attrs"
    @update:model-value="emit('update:modelValue', $event)"
    @change="emit('change', $event)"
  >
    <slot />
  </el-select>
</template>

<style scoped>
.dsms-filterable-select {
  width: 100%;
}
</style>
