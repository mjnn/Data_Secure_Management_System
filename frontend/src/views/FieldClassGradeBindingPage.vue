<template>
  <section class="cgb dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="cgb-title">
    <header class="cgb__header">
      <h3 id="cgb-title" class="cgb__title">数据字段绑定</h3>
      <p class="cgb__lead">
        为<strong>数据字段主表</strong>条目指定密级，写入 <code class="cgb__code">grade_label</code>（与「密级定义」中的名称一致）。数据来自后端
        <code class="cgb__code">/fields/class-grade</code>。
      </p>
    </header>

    <el-card class="cgb__form-card" shadow="never">
      <template #header>
        <span class="cgb__card-title">配置绑定</span>
      </template>
      <el-form label-width="120px" class="cgb__form" @submit.prevent>
        <el-form-item label="数据字段" required>
          <dsms-filterable-select
            v-model="selectedFieldId"
            placeholder="搜索并选择数据字段"
            @change="onFieldChange"
          >
            <el-option v-for="f in fieldOptions" :key="f.id" :label="f.label" :value="f.id" />
          </dsms-filterable-select>
        </el-form-item>
        <el-form-item label="密级" required>
          <dsms-filterable-select
            v-model="selectedGradeLabel"
            placeholder="搜索并选择密级"
            :disabled="!gradeOptions.length"
          >
            <el-option v-for="g in gradeOptions" :key="g.id" :label="gradeOptionLabel(g)" :value="g.label" />
          </dsms-filterable-select>
          <p v-if="!gradeOptions.length" class="cgb__field-hint">请先在「密级定义」中新增至少一种密级。</p>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="notes" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="可选" />
        </el-form-item>
        <div class="cgb__form-actions">
          <el-button type="primary" :disabled="!canSave" @click="onSave">保存绑定</el-button>
          <el-button :disabled="!selectedFieldId" @click="onClear">清除绑定</el-button>
        </div>
      </el-form>
    </el-card>

    <el-table class="cgb__table" :data="bindingRows" border stripe empty-text="暂无数据字段">
      <el-table-column prop="label" label="数据字段" min-width="200" show-overflow-tooltip />
      <el-table-column prop="grade_label" label="密级 (grade_label)" width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag v-if="row.grade_label" size="small" type="info">{{ row.grade_label }}</el-tag>
          <span v-else class="cgb__muted">未绑定</span>
        </template>
      </el-table-column>
      <el-table-column prop="grade_notes" label="备注" min-width="160" show-overflow-tooltip />
      <el-table-column label="更新日期" width="120">
        <template #default="{ row }">
          {{ row.grade_updatedAt || "—" }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="loadRowIntoForm(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import {
  deleteFieldClassGrade,
  fetchFieldClassGrades,
  fetchSensitivityLevels,
  putFieldClassGrades
} from "../api/dsmsSpaceApi.js";
import { fetchFieldCatalog, PORTAL_DATA_REFRESH_EVENT } from "../api/portalApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { loadFieldCatalogWithGradeBindings } from "../data/fieldClassGradeBindingMock.js";
import { loadSensitivityLevels } from "../data/sensitivityLevelMock.js";

const { tenantId, spaceId, ready } = usePortalTenantContext();
const refreshTick = ref(0);

const selectedFieldId = ref("");
const selectedGradeLabel = ref("");
const notes = ref("");

function bumpLocal() {
  refreshTick.value++;
}

async function reloadAll() {
  if (!tenantId.value) return;
  await Promise.all([
    fetchFieldCatalog(tenantId.value, spaceId.value),
    fetchFieldClassGrades(tenantId.value, spaceId.value),
    fetchSensitivityLevels(tenantId.value, spaceId.value)
  ]);
  bumpLocal();
}

watch([ready, tenantId, spaceId], () => {
  if (ready.value) reloadAll();
});

const fieldOptions = computed(() => {
  void refreshTick.value;
  return [...loadFieldCatalogWithGradeBindings()].sort((a, b) =>
    String(a.label).localeCompare(String(b.label), "zh-Hans-CN")
  );
});

const gradeOptions = computed(() => {
  void refreshTick.value;
  return loadSensitivityLevels();
});

function gradeOptionLabel(g) {
  return g.code ? `${g.label}（${g.code}）` : g.label;
}

const bindingRows = computed(() => {
  void refreshTick.value;
  return loadFieldCatalogWithGradeBindings();
});

const canSave = computed(
  () => Boolean(selectedFieldId.value && selectedGradeLabel.value && gradeOptions.value.length)
);

function onFieldChange() {
  const row = bindingRows.value.find((r) => r.id === selectedFieldId.value);
  if (!row) {
    selectedGradeLabel.value = "";
    notes.value = "";
    return;
  }
  selectedGradeLabel.value = row.grade_label || "";
  notes.value = row.grade_notes || "";
}

async function onSave() {
  const entryId = selectedFieldId.value;
  if (!entryId || !selectedGradeLabel.value) return;
  try {
    await putFieldClassGrades(tenantId.value, spaceId.value, [
      {
        field_catalog_entry_id: entryId,
        grade_label: selectedGradeLabel.value,
        notes: notes.value
      }
    ]);
    ElMessage.success("已保存密级绑定。");
    await reloadAll();
    onFieldChange();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  }
}

async function onClear() {
  const entryId = selectedFieldId.value;
  if (!entryId) return;
  try {
    await deleteFieldClassGrade(tenantId.value, spaceId.value, entryId);
    ElMessage.success("已清除密级绑定。");
    selectedGradeLabel.value = "";
    notes.value = "";
    await reloadAll();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "清除失败");
  }
}

function loadRowIntoForm(row) {
  selectedFieldId.value = row.id;
  onFieldChange();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function onExternalPersist() {
  reloadAll();
}

onMounted(() => {
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onExternalPersist);
  if (ready.value) reloadAll();
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onExternalPersist);
});
</script>

<style scoped>
.cgb {
  padding: 24px 28px 32px;
}

.cgb__header {
  margin-bottom: 20px;
}

.cgb__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.cgb__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.cgb__code {
  font-size: 0.8125rem;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--dsms-page-bg, #f4f6f9);
}

.cgb__form-card {
  margin-bottom: 20px;
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.cgb__card-title {
  font-weight: 600;
  color: var(--dsms-text);
}

.cgb__form {
  max-width: 640px;
}

.cgb__field-hint {
  margin: 6px 0 0;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}

.cgb__form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cgb__table {
  width: 100%;
}

.cgb__muted {
  color: var(--dsms-text-secondary);
  font-size: 0.875rem;
}
</style>
