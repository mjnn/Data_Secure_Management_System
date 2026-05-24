<template>
  <el-table :data="rows" :loading="loading" stripe>
    <el-table-column label="字段 Key" :width="enableFieldKeyEdit ? 200 : 180">
      <template #default="scope">
        <el-input
          v-if="enableFieldKeyEdit && !scope.row.is_builtin"
          v-model="scope.row.field_key"
          maxlength="64"
          placeholder="小写字母、数字、下划线"
          :disabled="isRowStructureLocked(scope.row)"
        />
        <span v-else>{{ scope.row.field_key }}</span>
      </template>
    </el-table-column>
    <el-table-column label="字段名称" width="180">
      <template #default="scope">
        <el-input v-model="scope.row.label" :disabled="isRowStructureLocked(scope.row)" />
      </template>
    </el-table-column>
    <el-table-column label="展示形式" width="160">
      <template #default="scope">
        <el-select v-model="scope.row.input_type" style="width: 100%" :disabled="isRowStructureLocked(scope.row)">
          <el-option v-for="item in inputTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </template>
    </el-table-column>
    <el-table-column label="填写说明" min-width="260">
      <template #default="scope">
        <el-input
          v-model="scope.row.help_text"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
          placeholder="鼠标悬停时展示"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="必填" width="90">
      <template #default="scope">
        <el-switch v-model="scope.row.required" :disabled="isRowStructureLocked(scope.row)" />
      </template>
    </el-table-column>
    <el-table-column label="最小长度" width="130">
      <template #default="scope">
        <el-input-number
          v-model="scope.row.min_length"
          :min="0"
          :max="5000"
          controls-position="right"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="最大长度" width="130">
      <template #default="scope">
        <el-input-number
          v-model="scope.row.max_length"
          :min="0"
          :max="5000"
          controls-position="right"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="正则" min-width="200">
      <template #default="scope">
        <el-input
          v-model="scope.row.regex_pattern"
          maxlength="500"
          placeholder="可选，如 ^[A-Za-z0-9_]+$"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="正则错误提示" min-width="200">
      <template #default="scope">
        <el-input
          v-model="scope.row.regex_error_message"
          maxlength="200"
          placeholder="可选"
          :disabled="isRowStructureLocked(scope.row)"
        />
      </template>
    </el-table-column>
    <el-table-column label="允许值 / 选项" min-width="220">
      <template #default="scope">
        <template v-if="scope.row.input_type === 'text' || scope.row.input_type === 'textarea'">
          <el-input
            v-model="scope.row.allowed_values_text"
            placeholder="可选；逗号分隔，填写后仅允许这些值"
            :disabled="isAllowedValuesLocked(scope.row)"
          />
        </template>
        <template v-else>
          <el-button type="primary" link :disabled="isAllowedValuesLocked(scope.row)" @click="openOptionsDialog(scope.row)">
            {{ selectOptionsSummary(scope.row) }}
          </el-button>
        </template>
      </template>
    </el-table-column>
    <el-table-column v-if="enableSortReorder" label="顺序" width="148" fixed="right">
      <template #default="scope">
        <el-button link type="primary" :disabled="isMoveUpDisabled(scope.$index)" @click="moveRowUp(scope.$index)">
          上移
        </el-button>
        <el-button link type="primary" :disabled="isMoveDownDisabled(scope.$index)" @click="moveRowDown(scope.$index)">
          下移
        </el-button>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="120" fixed="right">
      <template #default="scope">
        <el-button type="danger" size="small" link :disabled="isRowDeleteDisabled(scope.row)" @click="$emit('delete', scope.row)">
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>

  <el-dialog
    v-model="optionsDialogVisible"
    :title="optionsDialogTitle"
    width="800px"
    destroy-on-close
    @closed="optionsDialogRow = null"
  >
    <template v-if="optionsDialogRow">
      <slot name="selectOptionsEditor" :row="optionsDialogRow">
        <select-option-values-editor v-model:text="optionsDialogRow.allowed_values_text" />
      </slot>
    </template>
    <template #footer>
      <el-button
        v-if="optionsDialogRow && loadDistinctValuesByFieldKey"
        :loading="collectingDistinctValues"
        @click="fillDistinctOptionsFromFieldValues(optionsDialogRow)"
      >
        使用该字段已有值（去重）
      </el-button>
      <el-button type="primary" @click="optionsDialogVisible = false">完成</el-button>
    </template>
  </el-dialog>

  <div class="action-row">
    <p v-if="enableSortReorder" class="field-order-hint">{{ orderHintResolved }}</p>
    <el-button type="primary" :loading="saving" @click="$emit('save')">保存字段配置</el-button>
    <el-button @click="$emit('refresh')">刷新</el-button>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import SelectOptionValuesEditor from "./SelectOptionValuesEditor.vue";
import { FIELD_CONFIG_MANAGER_ORDER_HINT_DEFAULT } from "./fieldConfigManagerConstants.js";

const props = defineProps({
  rows: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  inputTypeOptions: { type: Array, required: true },
  deleteDisabledFieldKeys: { type: Array, default: () => [] },
  structureLockedFieldKeys: { type: Array, default: () => [] },
  /** 禁止编辑「逗号分隔允许值 / 配置选项」的 field_key */
  allowedValuesLockedFieldKeys: { type: Array, default: () => [] },
  loadDistinctValuesByFieldKey: { type: Function, default: undefined },
  enableSortReorder: { type: Boolean, default: true },
  sortReorderLockedFieldKeys: { type: Array, default: () => [] },
  lockBuiltinSortReorder: { type: Boolean, default: false },
  orderHint: { type: String, default: null },
  /** 非内置行是否允许编辑字段 Key（生命周期元字段等场景） */
  enableFieldKeyEdit: { type: Boolean, default: false }
});

defineEmits(["save", "refresh", "delete"]);

const orderHintResolved = computed(() => {
  const t = props.orderHint?.trim();
  return t || FIELD_CONFIG_MANAGER_ORDER_HINT_DEFAULT;
});

const isRowStructureLocked = (row) => props.structureLockedFieldKeys.includes(row.field_key);

const isRowDeleteDisabled = (row) => Boolean(row.is_builtin) || props.deleteDisabledFieldKeys.includes(row.field_key);

const isAllowedValuesLocked = (row) => props.allowedValuesLockedFieldKeys.includes(row.field_key);

const isRowSortLocked = (row) =>
  props.sortReorderLockedFieldKeys.includes(row.field_key) || (props.lockBuiltinSortReorder && Boolean(row.is_builtin));

const isMoveUpDisabled = (index) => {
  if (index <= 0) return true;
  const cur = props.rows[index];
  const prev = props.rows[index - 1];
  return isRowSortLocked(cur) || isRowSortLocked(prev);
};

const isMoveDownDisabled = (index) => {
  if (index >= props.rows.length - 1) return true;
  const cur = props.rows[index];
  const next = props.rows[index + 1];
  return isRowSortLocked(cur) || isRowSortLocked(next);
};

const syncSortOrderAfterReorder = () => {
  props.rows.forEach((row, i) => {
    row.sort_order = i;
  });
};

const moveRowUp = (index) => {
  if (isMoveUpDisabled(index)) return;
  const arr = props.rows;
  const row = arr.splice(index, 1)[0];
  arr.splice(index - 1, 0, row);
  syncSortOrderAfterReorder();
};

const moveRowDown = (index) => {
  if (isMoveDownDisabled(index)) return;
  const arr = props.rows;
  const row = arr.splice(index, 1)[0];
  arr.splice(index + 1, 0, row);
  syncSortOrderAfterReorder();
};

const optionsDialogVisible = ref(false);
const optionsDialogRow = ref(null);
const collectingDistinctValues = ref(false);

const optionsDialogTitle = computed(() => {
  const row = optionsDialogRow.value;
  if (!row) return "选项定义";
  return `选项定义 — ${row.label}（${row.field_key}）`;
});

const selectOptionsSummary = (row) => {
  const n = (row.allowed_values_text || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean).length;
  return n ? `已配置 ${n} 个选项` : "配置选项";
};

const openOptionsDialog = (row) => {
  if (isAllowedValuesLocked(row)) return;
  optionsDialogRow.value = row;
  optionsDialogVisible.value = true;
};

const fillDistinctOptionsFromFieldValues = async (row) => {
  if (!props.loadDistinctValuesByFieldKey) return;
  collectingDistinctValues.value = true;
  try {
    const values = await props.loadDistinctValuesByFieldKey(row.field_key);
    const current = (row.allowed_values_text || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const merged = Array.from(
      new Set([...current, ...(values || []).map((v) => String(v || "").trim()).filter(Boolean)])
    );
    row.allowed_values_text = merged.join(", ");
    ElMessage.success(`已合并 ${merged.length} 个去重选项`);
  } catch (error) {
    ElMessage.error(error?.message || "读取该字段已有值失败");
  } finally {
    collectingDistinctValues.value = false;
  }
};
</script>

<style scoped>
.action-row {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.field-order-hint {
  width: 100%;
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--dsms-text-secondary, #606266);
}
</style>
