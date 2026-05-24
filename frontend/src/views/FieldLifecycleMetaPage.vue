<template>
  <section class="flm dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="flm-title">
    <header class="flm__header dsms-animate-stagger-1">
      <h2 id="flm-title" class="flm__title">数据安全生命周期元字段</h2>
      <p v-if="!me" class="flm__lead">正在加载当前用户…</p>
      <p v-else class="flm__lead">
        由<strong>数据安全 FO / 系统管理员</strong>配置功能 FO 填报表：系统<strong>默认内置并锁定</strong>「数据字段」「业务功能」两条<strong>必填单选</strong>（顺序固定于表首）；其后可追加更多动态列。配置写入
        <code class="flm__code">{{ storageKey }}</code>；联调后对接规格中的空间内表单配置接口。
      </p>
    </header>

    <template v-if="me && isSecOrAdmin">
      <el-alert
        class="flm__alert dsms-animate-stagger-2"
        type="info"
        :closable="false"
        show-icon
        title="与 ref/dynamic field 对齐"
        description="管理端使用 FieldConfigManagerTable；下方「填报预览」与功能 FO 在填报任务中使用的 FoLifecycleFillTable 一致（含数据字段、业务功能列与动态列）。"
      />

      <div class="flm__toolbar dsms-animate-stagger-2">
        <el-button type="primary" @click="onAddField">新增字段</el-button>
      </div>

      <field-config-manager-table
        class="flm__table-wrap dsms-animate-stagger-3"
        :rows="rows"
        :loading="loading"
        :saving="saving"
        :input-type-options="inputTypeOptions"
        :enable-field-key-edit="true"
        :allowed-values-locked-field-keys="[LIFECYCLE_BUILTIN_DATA_FIELD_KEY]"
        :structure-locked-field-keys="builtinLockedKeys"
        :delete-disabled-field-keys="builtinLockedKeys"
        :sort-reorder-locked-field-keys="builtinLockedKeys"
        :lock-builtin-sort-reorder="true"
        @save="onSave"
        @refresh="onRefresh"
        @delete="onDelete"
      />

      <el-card class="flm__preview dsms-animate-stagger-4" shadow="never">
        <template #header>
          <span class="flm__preview-title">填报预览（功能 FO 视角 · 与填报任务明细表一致）</span>
        </template>
        <p class="flm__preview-hint">
          与功能 FO 在「填报任务管理」中打开的<strong>明细表</strong>同一套组件与列顺序：首列为<strong>数据字段</strong>，第二列为<strong>业务功能</strong>（绑定多项时可筛选单选；当前模拟绑定见
          <code class="flm__code">MOCK_FO_BOUND_FUNCTION_IDS</code>），其后为自定义动态列。可<strong>新增条目</strong>试填；预览数据<strong>不会</strong>写入任务或 session。当字段 Key、类型、必填、选项或最大长度变化时，预览表会<strong>重置为 1 行</strong>以免列错位。
        </p>
        <div class="flm__preview-table">
          <fo-lifecycle-fill-table
            v-model="previewTableRows"
            :columns="foPreviewColumns"
            :bound-function-ids="previewFoBoundFunctionIds"
            :function-name="functionNameById"
          />
        </div>
      </el-card>
    </template>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import api from "../api";
import FieldConfigManagerTable from "../components/form-config/FieldConfigManagerTable.vue";
import FoLifecycleFillTable from "../components/FoLifecycleFillTable.vue";
import {
  buildEmptyLifecycleFillRow,
  createEmptyLifecycleFieldTableRow,
  LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY,
  LIFECYCLE_BUILTIN_DATA_FIELD_KEY,
  LIFECYCLE_FIELD_CONFIG_STORAGE_KEY,
  loadLifecycleFieldConfigTableRows,
  mergeWithBuiltinLifecycleRows,
  parseAllowedValuesCommaText,
  persistLifecycleFieldConfigFromTableRows
} from "../data/lifecycleFieldConfigMock.js";
import { submissionFunctionById } from "../data/submissionTasksMock.js";
import { DATA_FIELD_CATALOG_PERSIST_EVENT } from "../data/dataFieldCatalogMock.js";
import { MOCK_FO_BOUND_FUNCTION_IDS } from "../composables/useSubmissionTaskFoReminderCount.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const router = useRouter();
const me = ref(null);
const rows = ref([]);
const loading = ref(false);
const saving = ref(false);
const previewTableRows = ref([]);
const catalogRefreshTick = ref(0);

function onCatalogPersisted() {
  catalogRefreshTick.value++;
}

const storageKey = LIFECYCLE_FIELD_CONFIG_STORAGE_KEY;

const builtinLockedKeys = [LIFECYCLE_BUILTIN_DATA_FIELD_KEY, LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY];

const previewFoBoundFunctionIds = MOCK_FO_BOUND_FUNCTION_IDS;

function functionNameById(id) {
  return submissionFunctionById(id)?.name || id;
}

const foPreviewColumns = computed(() => {
  void catalogRefreshTick.value;
  return mergeWithBuiltinLifecycleRows(rows.value).map((c) => {
    const allowed =
      Array.isArray(c.allowed_values) && c.allowed_values.length
        ? [...c.allowed_values]
        : parseAllowedValuesCommaText(c.allowed_values_text);
    return {
      field_key: c.field_key,
      label: c.label,
      input_type: c.input_type,
      required: c.required,
      help_text: c.help_text,
      max_length: c.max_length,
      allowed_values: allowed
    };
  });
});

/** 列结构变化时重置预览行，避免增删列后与旧行数据错位（不含列标题文案） */
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

function resetPreviewTableRows() {
  const cols = foPreviewColumns.value;
  if (!cols.length) {
    previewTableRows.value = [];
    return;
  }
  const keys = cols.map((c) => c.field_key);
  let next = [buildEmptyLifecycleFillRow(keys, cols)];
  if (previewFoBoundFunctionIds.length === 1) {
    const fid = previewFoBoundFunctionIds[0];
    next = next.map((r) => ({ ...r, [LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY]: fid }));
  }
  previewTableRows.value = next;
}

watch(previewColumnFingerprint, resetPreviewTableRows, { immediate: true });

const isSecOrAdmin = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

const inputTypeOptions = [
  { label: "单行文本", value: "text" },
  { label: "多行文本", value: "textarea" },
  { label: "单选", value: "single_select" },
  { label: "多选", value: "multi_select" }
];

function reloadRows() {
  loading.value = true;
  try {
    rows.value = loadLifecycleFieldConfigTableRows();
  } finally {
    loading.value = false;
  }
}

const FIELD_KEY_RE = /^[a-z][a-z0-9_]*$/;

function validateBeforeSave() {
  const list = rows.value;
  if (!list.length) return true;
  const keys = new Set();
  for (const row of list) {
    const k = String(row.field_key || "").trim();
    if (!k) {
      ElMessage.error("字段 Key 不能为空。");
      return false;
    }
    if (!FIELD_KEY_RE.test(k)) {
      ElMessage.error(`字段 Key 须为小写蛇形（^[a-z][a-z0-9_]*$）：${k}`);
      return false;
    }
    if (keys.has(k)) {
      ElMessage.error(`字段 Key 重复：${k}`);
      return false;
    }
    keys.add(k);
    if (!String(row.label || "").trim()) {
      ElMessage.error(`请填写字段名称（${k}）。`);
      return false;
    }
    const minL = row.min_length != null ? Number(row.min_length) : null;
    const maxL = row.max_length != null ? Number(row.max_length) : null;
    if (minL != null && maxL != null && minL > maxL) {
      ElMessage.error(`最小长度不能大于最大长度（${k}）。`);
      return false;
    }
    if (row.regex_pattern) {
      try {
        new RegExp(row.regex_pattern);
      } catch {
        ElMessage.error(`正则表达式无效（${k}）。`);
        return false;
      }
    }
    if (row.input_type === "single_select" || row.input_type === "multi_select") {
      const opts = parseAllowedValuesCommaText(row.allowed_values_text);
      if (!opts.length && row.field_key !== LIFECYCLE_BUILTIN_BUSINESS_FUNCTION_KEY) {
        ElMessage.error(`单选/多选须配置至少一个选项（${k}）。`);
        return false;
      }
    }
  }
  return true;
}

async function onSave() {
  if (!validateBeforeSave()) return;
  saving.value = true;
  try {
    persistLifecycleFieldConfigFromTableRows(rows.value);
    rows.value = loadLifecycleFieldConfigTableRows();
    ElMessage.success(rows.value.length ? "已保存字段配置（模拟）。" : "已清空字段配置（模拟）。");
  } finally {
    saving.value = false;
  }
}

function onRefresh() {
  reloadRows();
  ElMessage.success("已从本地存储重新加载。");
}

function onAddField() {
  rows.value.push(createEmptyLifecycleFieldTableRow(rows.value.length));
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除字段「${row.label}」（${row.field_key}）吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  const idx = rows.value.indexOf(row);
  if (idx >= 0) rows.value.splice(idx, 1);
  rows.value.forEach((r, i) => {
    r.sort_order = i;
  });
}

const loadMe = async () => {
  try {
    const { data } = await api.get("/api/v1/users/me");
    me.value = data;
    const role = effectivePlatformRole(data);
    if (role !== PLATFORM_ROLE.SYSTEM_ADMIN && role !== PLATFORM_ROLE.SECURITY_FO) {
      ElMessage.warning("当前角色无权访问数据安全生命周期元字段配置。");
      await router.replace({ name: "dashboard-home" });
    }
  } catch {
    /* 未登录由全局守卫处理 */
  }
};

onMounted(() => {
  window.addEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onCatalogPersisted);
});

onBeforeUnmount(() => {
  window.removeEventListener(DATA_FIELD_CATALOG_PERSIST_EVENT, onCatalogPersisted);
});

reloadRows();

loadMe();
</script>

<style scoped>
.flm {
  padding: 24px 28px 32px;
}

.flm__header {
  margin-bottom: 20px;
}

.flm__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.flm__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.flm__code {
  padding: 1px 6px;
  font-size: 0.8125rem;
  border-radius: 4px;
  background: var(--dsms-fill-light, #f5f7fa);
  color: var(--dsms-text);
}

.flm__alert {
  margin-bottom: 16px;
}

.flm__toolbar {
  margin-bottom: 12px;
}

.flm__table-wrap {
  width: 100%;
}

.flm__preview {
  margin-top: 24px;
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.flm__preview-title {
  font-weight: 600;
  color: var(--dsms-text);
}

.flm__preview-hint {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.flm__preview-table {
  width: 100%;
  overflow-x: auto;
}
</style>
