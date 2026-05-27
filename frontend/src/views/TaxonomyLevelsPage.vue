<template>
  <section class="txl dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="txl-title">
      <header class="txl__header">
        <h3 id="txl-title" class="txl__title">分类树层级</h3>
        <p class="txl__lead">
          维护分类级 <strong>0（根级）</strong>、<strong>1、2、3…</strong>。数据来自
          <code class="txl__code">/taxonomy-levels</code>；亦可使用 Excel 模板批量导入（文档资源模块
          <code class="txl__code">taxonomy_level</code>）。
        </p>
      </header>

      <div class="txl__toolbar">
        <el-button type="primary" @click="openCreate">新增层级</el-button>
        <el-button @click="reloadLevels">刷新</el-button>
        <el-button @click="downloadTemplate">下载模板</el-button>
        <el-button @click="pickImport">Excel 导入</el-button>
        <el-button :loading="exporting" @click="runExport">导出 Excel</el-button>
        <el-button type="primary" plain @click="goNodes">下一步：分类树节点</el-button>
      </div>
      <input ref="importInputRef" type="file" accept=".xlsx" class="txl__file-input" @change="onImportFile" />

      <el-table
        class="txl__table"
        :data="levelRows"
        row-key="id"
        border
        stripe
        empty-text="暂无分类树层级，请点击「新增层级」或导入 Excel"
      >
        <el-table-column label="分类级" width="120">
          <template #default="{ row }">
            <el-tag :type="row.level === 0 ? 'primary' : 'info'" size="small">
              {{ formatLevel(row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="层级名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
        <el-table-column prop="updatedAt" label="更新日期" width="120" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row, $index }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
            <el-button link :disabled="$index === 0" @click="onMove(row, 'up')">上移</el-button>
            <el-button link :disabled="$index === levelRows.length - 1" @click="onMove(row, 'down')">
              下移
            </el-button>
          </template>
        </el-table-column>
      </el-table>
  </section>

  <el-dialog
    v-model="editVisible"
    class="txl-edit-dialog"
    :title="editMode === 'create' ? '新增分类树层级' : '编辑分类树层级'"
    width="520px"
    append-to-body
    align-center
    destroy-on-close
    @closed="resetEditForm"
  >
    <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="96px">
      <el-form-item label="分类级" prop="level">
        <dsms-filterable-select v-model="editForm.level" placeholder="搜索并选择分类级" class="txl__level-select">
          <el-option
            v-for="n in levelOptionsForForm"
            :key="n"
            :label="formatLevel(n)"
            :value="n"
          />
        </dsms-filterable-select>
        <p class="txl__field-hint">0 表示根级；1、2、3… 表示自上而下第几级分类。</p>
      </el-form-item>
      <el-form-item label="层级名称" prop="name">
        <el-input v-model="editForm.name" maxlength="100" show-word-limit placeholder="如：根级、一级、二级" />
      </el-form-item>
      <el-form-item label="说明" prop="description">
        <el-input v-model="editForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible = false">取消</el-button>
      <el-button type="primary" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import api from "../api";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import {
  createTaxonomyLevel,
  deleteTaxonomyLevel,
  fetchTaxonomyLevels,
  updateTaxonomyLevel
} from "../api/dsmsSpaceApi.js";
import { PORTAL_DATA_REFRESH_EVENT } from "../api/portalApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import {
  formatTaxonomyLevelLabel,
  listAvailableLevelNumbers,
  loadTaxonomyLevels,
  TAXONOMY_LEVEL_PERSIST_EVENT
} from "../data/taxonomyLevelMock.js";

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const refreshTick = ref(0);
const exporting = ref(false);
const importInputRef = ref(null);

const levelRows = computed(() => {
  void refreshTick.value;
  return loadTaxonomyLevels();
});

function formatLevel(level) {
  return formatTaxonomyLevelLabel(level);
}

function bumpLocal() {
  refreshTick.value++;
}

async function reloadLevels() {
  if (!tenantId.value) return;
  try {
    await fetchTaxonomyLevels(tenantId.value, spaceId.value);
    bumpLocal();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载分类树层级失败");
  }
}

watch([ready, tenantId, spaceId], () => {
  if (ready.value) reloadLevels();
});

const editVisible = ref(false);
const editMode = ref("create");
const editingId = ref("");
const editFormRef = ref(null);
const editForm = ref({
  level: 0,
  name: "",
  description: ""
});

const editRules = {
  level: [{ required: true, message: "请选择分类级", trigger: "change" }],
  name: [{ required: true, message: "请输入层级名称", trigger: "blur" }]
};

const levelOptionsForForm = computed(() => {
  void refreshTick.value;
  if (editMode.value === "edit" && editingId.value) {
    const current = levelRows.value.find((r) => r.id === editingId.value);
    const avail = listAvailableLevelNumbers(editingId.value);
    if (current && !avail.includes(current.level)) {
      return [...avail, current.level].sort((a, b) => a - b);
    }
    return avail;
  }
  const avail = listAvailableLevelNumbers();
  return avail.length ? avail : [levelRows.value.length];
});

function openCreate() {
  editMode.value = "create";
  editingId.value = "";
  const avail = listAvailableLevelNumbers();
  const defaultLevel = avail.length ? avail[0] : levelRows.value.length;
  editForm.value = {
    level: defaultLevel,
    name: defaultLevel === 0 ? "根级" : `${defaultLevel} 级`,
    description: ""
  };
  editVisible.value = true;
}

function openEdit(row) {
  editMode.value = "edit";
  editingId.value = row.id;
  editForm.value = {
    level: row.level,
    name: row.name || "",
    description: row.description || ""
  };
  editVisible.value = true;
}

function resetEditForm() {
  editFormRef.value?.clearValidate?.();
}

async function submitEdit() {
  const form = editFormRef.value;
  if (!form) return;
  try {
    await form.validate();
  } catch {
    return;
  }
  const payload = {
    level: editForm.value.level,
    name: editForm.value.name.trim(),
    description: editForm.value.description?.trim() || null,
    sort_order: editForm.value.level
  };
  try {
    if (editMode.value === "create") {
      await createTaxonomyLevel(tenantId.value, spaceId.value, payload);
      ElMessage.success("已新增分类树层级。");
    } else {
      const row = levelRows.value.find((r) => r.id === editingId.value);
      await updateTaxonomyLevel(tenantId.value, spaceId.value, row?._apiId || editingId.value, {
        ...payload,
        sort_order: row?.sort_order ?? payload.sort_order
      });
      ElMessage.success("已保存修改。");
    }
    editVisible.value = false;
    await reloadLevels();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${formatLevel(row.level)} · ${row.name}」吗？`,
      "删除确认",
      { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await deleteTaxonomyLevel(tenantId.value, spaceId.value, row._apiId || row.id);
    ElMessage.success("已删除分类树层级。");
    await reloadLevels();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败");
  }
}

async function onMove(row, direction) {
  const list = [...levelRows.value].sort((a, b) => a.sort_order - b.sort_order || a.level - b.level);
  const idx = list.findIndex((r) => r.id === row.id);
  if (idx < 0) return;
  const target = direction === "up" ? idx - 1 : idx + 1;
  if (target < 0 || target >= list.length) {
    ElMessage.warning(direction === "up" ? "已在最上级。" : "已在最下级。");
    return;
  }
  const current = list[idx];
  const neighbor = list[target];
  try {
    await updateTaxonomyLevel(tenantId.value, spaceId.value, current._apiId || current.id, {
      level: neighbor.level,
      name: current.name,
      description: current.description || null,
      sort_order: neighbor.sort_order
    });
    await updateTaxonomyLevel(tenantId.value, spaceId.value, neighbor._apiId || neighbor.id, {
      level: current.level,
      name: neighbor.name,
      description: neighbor.description || null,
      sort_order: current.sort_order
    });
    ElMessage.success("已调整顺序。");
    await reloadLevels();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "排序失败");
  }
}

async function downloadTemplate() {
  try {
    const res = await api.get(`/api/v1/dsms/tenants/${tenantId.value}/documents/modules/taxonomy_level/template`, {
      responseType: "blob"
    });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = "taxonomy_level_template.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "下载模板失败");
  }
}

function pickImport() {
  importInputRef.value?.click();
}

async function onImportFile(ev) {
  const file = ev.target.files?.[0];
  ev.target.value = "";
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    await api.post(
      `/api/v1/dsms/tenants/${tenantId.value}/spaces/${spaceId.value}/documents/import?module_key=taxonomy_level`,
      fd,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    ElMessage.success("导入完成");
    await reloadLevels();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "导入失败");
  }
}

async function runExport() {
  exporting.value = true;
  try {
    const { data } = await api.post(
      `/api/v1/dsms/tenants/${tenantId.value}/spaces/${spaceId.value}/documents/export`,
      { module_key: "taxonomy_level" }
    );
    if (data?.result_resource_id) {
      const res = await api.get(
        `/api/v1/dsms/tenants/${tenantId.value}/documents/resources/${data.result_resource_id}/download`,
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "taxonomy_level_export.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    }
    ElMessage.success("导出完成");
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "导出失败");
  } finally {
    exporting.value = false;
  }
}

function onLevelsPersist() {
  reloadLevels();
}

function goNodes() {
  router.push({ name: "dashboard-rule-taxonomy-nodes" });
}

onMounted(() => {
  window.addEventListener(TAXONOMY_LEVEL_PERSIST_EVENT, onLevelsPersist);
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onLevelsPersist);
  if (ready.value) reloadLevels();
});

onBeforeUnmount(() => {
  window.removeEventListener(TAXONOMY_LEVEL_PERSIST_EVENT, onLevelsPersist);
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onLevelsPersist);
});
</script>

<style scoped>
.txl__header {
  margin-bottom: 20px;
}

.txl {
  padding: 24px 28px 32px;
}

.txl__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.txl__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.txl__code {
  font-size: 0.8125rem;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--dsms-page-bg, #f4f6f9);
}

.txl__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.txl__table {
  width: 100%;
}

.txl__level-select {
  width: 100%;
}

.txl__field-hint {
  margin: 6px 0 0;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}

.txl__file-input {
  display: none;
}
</style>
