<template>
  <section class="tfc dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="tfc-title">
      <header class="tfc__header">
        <h3 id="tfc-title" class="tfc__title">数据字段分类</h3>
        <p class="tfc__lead">
          为数据字段主表条目指定分类树位置，保存为 <code class="tfc__code">taxonomy_code</code>（与节点 code 一致）。数据来自
          <code class="tfc__code">/field-catalog</code> 与 <code class="tfc__code">/taxonomy/nodes</code>。
        </p>
      </header>

      <el-card class="tfc__form-card" shadow="never">
        <template #header>
          <span class="tfc__card-title">配置分类</span>
        </template>
        <el-form label-width="120px" class="tfc__form" @submit.prevent>
          <el-form-item label="数据字段" required>
            <dsms-filterable-select
              v-model="selectedFieldId"
              placeholder="搜索并选择数据字段"
              @change="onFieldChange"
            >
              <el-option
                v-for="f in fieldOptions"
                :key="f.id"
                :label="f.label"
                :value="f.id"
              />
            </dsms-filterable-select>
          </el-form-item>

          <template v-if="cascadeSteps.length">
            <el-form-item
              v-for="step in cascadeSteps"
              :key="step.level"
              :label="step.label"
              :required="step.required"
            >
              <dsms-filterable-select
                v-model="selectionByLevel[step.level]"
                :placeholder="step.placeholder"
                :disabled="step.disabled"
                @change="(val) => onLevelChange(step.level, val)"
              >
                <el-option
                  v-for="opt in step.options"
                  :key="opt.id"
                  :label="opt.optionLabel"
                  :value="opt.id"
                />
              </dsms-filterable-select>
              <p v-if="step.hint" class="tfc__field-hint">{{ step.hint }}</p>
            </el-form-item>
          </template>
          <p v-else class="tfc__field-hint tfc__field-hint--block">
            请先在「分类树层级」中配置层级，并在「分类树节点」中维护节点。
          </p>

          <el-form-item v-if="resolvedTaxonomyCode" label="taxonomy_code">
            <span class="tfc__code-readonly">{{ resolvedTaxonomyCode }}</span>
            <span class="tfc__path-preview">{{ pathPreview }}</span>
          </el-form-item>

          <div class="tfc__form-actions">
            <el-button type="primary" :disabled="!canSave" @click="onSave">保存分类</el-button>
            <el-button :disabled="!selectedFieldId" @click="onClear">清除分类</el-button>
          </div>
        </el-form>
      </el-card>

      <el-table
        class="tfc__table"
        :data="classificationRows"
        border
        stripe
        empty-text="暂无数据字段"
      >
        <el-table-column prop="label" label="数据字段" min-width="200" show-overflow-tooltip />
        <el-table-column label="分类路径" min-width="280" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.pathLabel }}
          </template>
        </el-table-column>
        <el-table-column prop="taxonomy_code" label="taxonomy_code" width="140" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.taxonomy_code || "—" }}
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新日期" width="120" />
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
import { fetchTaxonomyNodes } from "../api/dsmsSpaceApi.js";
import { fetchFieldCatalog, PORTAL_DATA_REFRESH_EVENT, updateFieldCatalogEntry } from "../api/portalApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { loadDataFieldCatalogEntries } from "../data/dataFieldCatalogMock.js";
import {
  formatTaxonomyPathByCode,
  getTaxonomyNodeById,
  listRegisteredTaxonomyLevelNumbers,
  listTaxonomyNodesByParent,
  resolveTaxonomyNodeIdPathFromCode,
  TAXONOMY_LEVEL_PERSIST_EVENT,
  TAXONOMY_NODE_PERSIST_EVENT,
  taxonomyLevelTitleForDepth
} from "../data/taxonomyNodeMock.js";
import { loadFieldCatalogWithTaxonomy } from "../data/fieldTaxonomyClassificationMock.js";

const { tenantId, spaceId, ready } = usePortalTenantContext();
const refreshTick = ref(0);

function bumpLocal() {
  refreshTick.value++;
}

async function reloadCatalogAndNodes() {
  if (!tenantId.value) return;
  try {
    await Promise.all([
      fetchFieldCatalog(tenantId.value, spaceId.value),
      fetchTaxonomyNodes(tenantId.value, spaceId.value)
    ]);
    bumpLocal();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载字段或分类节点失败");
  }
}

watch([ready, tenantId, spaceId], () => {
  if (ready.value) reloadCatalogAndNodes();
});

const fieldOptions = computed(() => {
  void refreshTick.value;
  return [...loadDataFieldCatalogEntries()].sort((a, b) =>
    String(a.label).localeCompare(String(b.label), "zh-Hans-CN")
  );
});

const classificationRows = computed(() => {
  void refreshTick.value;
  return loadFieldCatalogWithTaxonomy().map((e) => ({
    ...e,
    pathLabel: e.taxonomy_code ? formatTaxonomyPathByCode(e.taxonomy_code) : "未分类"
  }));
});

const registeredLevels = computed(() => {
  void refreshTick.value;
  return listRegisteredTaxonomyLevelNumbers();
});

/** level number -> selected node id */
const selectionByLevel = ref({});

const selectedFieldId = ref("");

function clearSelectionsFromLevel(fromLevel) {
  const levels = registeredLevels.value;
  const next = { ...selectionByLevel.value };
  let hit = false;
  for (const lv of levels) {
    if (lv === fromLevel) hit = true;
    if (hit) delete next[lv];
  }
  selectionByLevel.value = next;
}

function onLevelChange(level, _val) {
  clearSelectionsFromLevel(level + 1);
}

function onFieldChange() {
  const row = fieldOptions.value.find((f) => f.id === selectedFieldId.value);
  if (!row) {
    selectionByLevel.value = {};
    return;
  }
  const code = String(row.taxonomy_code || "").trim();
  if (!code) {
    selectionByLevel.value = {};
    return;
  }
  const idPath = resolveTaxonomyNodeIdPathFromCode(code);
  const next = {};
  for (const nid of idPath) {
    const node = getTaxonomyNodeById(nid);
    if (!node) continue;
    const depth = idPath.indexOf(nid);
    const levelNum = registeredLevels.value[depth];
    if (levelNum != null) next[levelNum] = nid;
  }
  selectionByLevel.value = next;
}

const cascadeSteps = computed(() => {
  void refreshTick.value;
  const levels = registeredLevels.value;
  if (!levels.length) return [];

  const steps = [];
  for (let i = 0; i < levels.length; i++) {
    const level = levels[i];
    const parentId = i === 0 ? null : selectionByLevel.value[levels[i - 1]];
    const disabled = i > 0 && !parentId;
    const options = disabled ? [] : listTaxonomyNodesByParent(parentId);
    const title = taxonomyLevelTitleForDepth(level);
    steps.push({
      level,
      label: `${formatLevelTag(level)} · ${title}`,
      required: options.length > 0,
      disabled,
      placeholder: disabled ? "请先选择上一级" : `搜索并选择${title}节点`,
      hint: disabled ? "" : options.length ? "" : "该父节点下暂无子节点，可保存上一级对应的 taxonomy_code。",
      options: options.map((n) => ({
        id: n.id,
        optionLabel: `${n.name}（${n.code}）`
      }))
    });
  }
  return steps;
});

function formatLevelTag(level) {
  return level === 0 ? "0（根级）" : `${level} 级`;
}

const deepestSelectedNode = computed(() => {
  const levels = registeredLevels.value;
  let last = null;
  for (const lv of levels) {
    const nid = selectionByLevel.value[lv];
    if (!nid) break;
    last = getTaxonomyNodeById(nid);
  }
  return last;
});

const resolvedTaxonomyCode = computed(() => deepestSelectedNode.value?.code || "");

const pathPreview = computed(() => {
  const code = resolvedTaxonomyCode.value;
  if (!code) return "";
  return `路径：${formatTaxonomyPathByCode(code)}`;
});

const canSave = computed(() => Boolean(selectedFieldId.value && resolvedTaxonomyCode.value));

function selectedFieldRow() {
  return fieldOptions.value.find((f) => f.id === selectedFieldId.value) || null;
}

async function onSave() {
  if (!selectedFieldId.value) {
    ElMessage.warning("请先选择数据字段。");
    return;
  }
  if (!resolvedTaxonomyCode.value) {
    ElMessage.warning("请按分类层级逐级选择，直至目标节点。");
    return;
  }
  const row = selectedFieldRow();
  if (!row) return;
  const entryId = row._apiId || row.id;
  try {
    await updateFieldCatalogEntry(tenantId.value, spaceId.value, entryId, {
      label: row.label,
      identifier_key: row.identifier_key,
      description: row.description,
      taxonomy_code: resolvedTaxonomyCode.value
    });
    ElMessage.success("已保存分类。");
    await reloadCatalogAndNodes();
    onFieldChange();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  }
}

async function onClear() {
  if (!selectedFieldId.value) return;
  const row = selectedFieldRow();
  if (!row) return;
  const entryId = row._apiId || row.id;
  try {
    await updateFieldCatalogEntry(tenantId.value, spaceId.value, entryId, {
      label: row.label,
      identifier_key: row.identifier_key,
      description: row.description,
      taxonomy_code: null
    });
    ElMessage.success("已清除该字段的分类。");
    selectionByLevel.value = {};
    await reloadCatalogAndNodes();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "清除失败");
  }
}

function loadRowIntoForm(row) {
  selectedFieldId.value = row.id;
  onFieldChange();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

watch(registeredLevels, () => {
  onFieldChange();
});

function onExternalPersist() {
  reloadCatalogAndNodes();
}

onMounted(() => {
  window.addEventListener(TAXONOMY_NODE_PERSIST_EVENT, onExternalPersist);
  window.addEventListener(TAXONOMY_LEVEL_PERSIST_EVENT, onExternalPersist);
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onExternalPersist);
  if (ready.value) reloadCatalogAndNodes();
});

onBeforeUnmount(() => {
  window.removeEventListener(TAXONOMY_NODE_PERSIST_EVENT, onExternalPersist);
  window.removeEventListener(TAXONOMY_LEVEL_PERSIST_EVENT, onExternalPersist);
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onExternalPersist);
});
</script>

<style scoped>
.tfc {
  padding: 24px 28px 32px;
}

.tfc {
  padding: 24px 28px 32px;
}

.tfc__header {
  margin-bottom: 20px;
}

.tfc__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.tfc__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.tfc__code {
  font-size: 0.8125rem;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--dsms-page-bg, #f4f6f9);
}

.tfc__form-card {
  margin-bottom: 20px;
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.tfc__card-title {
  font-weight: 600;
  color: var(--dsms-text);
}

.tfc__form {
  max-width: 640px;
}

.tfc__field-hint {
  margin: 6px 0 0;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}

.tfc__field-hint--block {
  margin: 0 0 12px;
}

.tfc__code-readonly {
  font-family: ui-monospace, monospace;
  font-size: 0.8125rem;
  color: var(--dsms-text);
}

.tfc__path-preview {
  display: block;
  margin-top: 4px;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.tfc__form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 4px;
}

.tfc__table {
  width: 100%;
}
</style>
