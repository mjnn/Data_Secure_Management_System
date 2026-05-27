<template>
  <section class="txn dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="txn-title">
      <header class="txn__header">
        <h3 id="txn-title" class="txn__title">分类树节点</h3>
        <p class="txn__lead">
          维护节点 <code class="txn__code">code</code>、<code class="txn__code">name</code> 与上级；深度须与「分类树层级」一致。数据来自后端
          <code class="txn__code">/taxonomy/nodes</code>。
        </p>
      </header>

      <div class="txn__toolbar">
        <el-button type="primary" @click="openCreateRoot">新增根节点</el-button>
        <el-button :disabled="!selectedRow" @click="openCreateChild(selectedRow)">为选中项新增子节点</el-button>
        <el-button type="primary" plain @click="goFieldClassification">下一步：数据字段分类</el-button>
      </div>

      <el-table
        ref="tableRef"
        class="txn__table"
        :data="treeRows"
        row-key="id"
        border
        stripe
        default-expand-all
        highlight-current-row
        :tree-props="{ children: 'children' }"
        empty-text="暂无分类节点，请先新增根节点"
        @current-change="onCurrentChange"
      >
        <el-table-column prop="name" label="节点名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="code" label="code" width="140" show-overflow-tooltip />
        <el-table-column label="分类级" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="taxonomyNodeDepth(row.id) === 0 ? 'primary' : 'info'">
              {{ formatLevelTag(taxonomyNodeDepth(row.id)) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上级路径" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ parentPathLabel(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="72" align="center" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openEdit(row)">编辑</el-button>
            <el-button link type="primary" @click.stop="openCreateChild(row)">子节点</el-button>
            <el-button link type="danger" @click.stop="onDelete(row)">删除</el-button>
            <el-button link @click.stop="onMove(row, 'up')">上移</el-button>
            <el-button link @click.stop="onMove(row, 'down')">下移</el-button>
          </template>
        </el-table-column>
      </el-table>
  </section>

  <el-dialog
    v-model="editVisible"
    class="txn-edit-dialog"
    :title="dialogTitle"
    width="560px"
    append-to-body
    align-center
    destroy-on-close
    @closed="resetEditForm"
  >
    <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="96px">
      <el-form-item label="上级节点" prop="parent_id">
        <dsms-filterable-select
          v-model="editForm.parent_id"
          placeholder="搜索上级（留空为根级）"
          :disabled="editMode === 'createChild'"
        >
          <el-option
            v-for="opt in parentOptionsForForm"
            :key="opt.id || '__root__'"
            :label="opt.label"
            :value="opt.id"
          />
        </dsms-filterable-select>
        <p v-if="editMode === 'createChild'" class="txn__field-hint">子节点上级已固定为当前父节点。</p>
        <p v-else class="txn__field-hint">
          根节点对应分类级 0；每向下一级深度 +1，最深不得超过「分类树层级」中已注册的最大级。
        </p>
      </el-form-item>
      <el-form-item label="节点 code" prop="code">
        <el-input
          v-model="editForm.code"
          maxlength="64"
          show-word-limit
          placeholder="空间内唯一，如 L2.VIN"
          :disabled="editMode === 'edit'"
        />
        <p v-if="editMode === 'edit'" class="txn__field-hint">编辑时不改 code，避免破坏已绑定的 taxonomy_code。</p>
      </el-form-item>
      <el-form-item label="节点名称" prop="name">
        <el-input v-model="editForm.name" maxlength="100" show-word-limit placeholder="如：VIN 码" />
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
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import {
  createTaxonomyNode,
  deleteTaxonomyNode,
  fetchTaxonomyNodes,
  updateTaxonomyNode
} from "../api/dsmsSpaceApi.js";
import { PORTAL_DATA_REFRESH_EVENT } from "../api/portalApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { loadFieldCatalogWithTaxonomy } from "../data/fieldTaxonomyClassificationMock.js";
import {
  formatTaxonomyLevelLabel,
  loadTaxonomyLevels,
  TAXONOMY_LEVEL_PERSIST_EVENT
} from "../data/taxonomyLevelMock.js";
import {
  buildTaxonomyNodeTree,
  canAddTaxonomyNodeUnderParent,
  formatTaxonomyNodePathById,
  getTaxonomyNodeById,
  listTaxonomyParentOptions,
  taxonomyNodeDepth,
  TAXONOMY_NODE_PERSIST_EVENT
} from "../data/taxonomyNodeMock.js";

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const flatNodes = ref([]);
const refreshTick = ref(0);
const tableRef = ref(null);
const selectedRow = ref(null);

function bumpLocal() {
  refreshTick.value++;
}

const treeRows = computed(() => {
  void refreshTick.value;
  return buildTaxonomyNodeTree();
});

async function loadNodes() {
  if (!ready.value || !tenantId.value) return;
  try {
    flatNodes.value = await fetchTaxonomyNodes(tenantId.value, spaceId.value);
    bumpLocal();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载分类节点失败");
  }
}

watch([ready, tenantId, spaceId], () => {
  if (ready.value) loadNodes();
});

function formatLevelTag(depth) {
  return formatTaxonomyLevelLabel(depth);
}

function parentPathLabel(row) {
  if (!row.parent_id) return "—";
  return formatTaxonomyNodePathById(row.parent_id);
}

function countFieldRefsByCode(code) {
  const c = String(code || "").trim();
  return loadFieldCatalogWithTaxonomy().filter((e) => e.taxonomy_code === c).length;
}

function onCurrentChange(row) {
  selectedRow.value = row || null;
}

const editVisible = ref(false);
const editMode = ref("createRoot");
const editingId = ref("");
const editFormRef = ref(null);
const editForm = ref({
  parent_id: "",
  code: "",
  name: ""
});

const editRules = {
  code: [{ required: true, message: "请输入节点 code", trigger: "blur" }],
  name: [{ required: true, message: "请输入节点名称", trigger: "blur" }]
};

const dialogTitle = computed(() => {
  if (editMode.value === "createRoot") return "新增根节点";
  if (editMode.value === "createChild") return "新增子节点";
  return "编辑分类节点";
});

const parentOptionsForForm = computed(() => {
  void refreshTick.value;
  const exclude = editMode.value === "edit" ? editingId.value : null;
  return listTaxonomyParentOptions(exclude);
});

function openCreateRoot() {
  editMode.value = "createRoot";
  editingId.value = "";
  editForm.value = { parent_id: "", code: "", name: "" };
  editVisible.value = true;
}

function openCreateChild(row) {
  if (!row?.id) return;
  if (!canAddTaxonomyNodeUnderParent(row.id)) {
    ElMessage.warning("该节点已在最深层级，无法新增子节点。请先在「分类树层级」扩展层级。");
    return;
  }
  editMode.value = "createChild";
  editingId.value = "";
  editForm.value = { parent_id: row.id, code: "", name: "" };
  editVisible.value = true;
}

function openEdit(row) {
  editMode.value = "edit";
  editingId.value = row.id;
  editForm.value = {
    parent_id: row.parent_id || "",
    code: row.code,
    name: row.name
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
  const parentId = editForm.value.parent_id || null;
  const payload = {
    code: editForm.value.code,
    name: editForm.value.name,
    parent_id: parentId
  };
  try {
    if (editMode.value === "edit") {
      await updateTaxonomyNode(tenantId.value, spaceId.value, editingId.value, payload);
      ElMessage.success("已保存节点。");
    } else {
      const siblings = flatNodes.value.filter((n) => (n.parent_id || null) === (parentId || null));
      const sort_order = siblings.length ? Math.max(...siblings.map((s) => s.sort_order)) + 1 : 0;
      await createTaxonomyNode(tenantId.value, spaceId.value, { ...payload, sort_order });
      ElMessage.success("已新增节点。");
    }
    editVisible.value = false;
    await loadNodes();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除节点「${row.name}」（${row.code}）吗？`,
      "删除确认",
      { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  const refs = countFieldRefsByCode(row.code);
  if (refs > 0) {
    ElMessage.error(`仍有 ${refs} 个数据字段引用该 code，无法删除。`);
    return;
  }
  try {
    await deleteTaxonomyNode(tenantId.value, spaceId.value, row.id);
    ElMessage.success("已删除节点。");
    if (selectedRow.value?.id === row.id) selectedRow.value = null;
    await loadNodes();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败");
  }
}

async function onMove(row, direction) {
  const pid = row.parent_id || null;
  const siblings = flatNodes.value
    .filter((n) => (n.parent_id || null) === pid)
    .sort((a, b) => a.sort_order - b.sort_order || a.code.localeCompare(b.code));
  const idx = siblings.findIndex((n) => n.id === row.id);
  if (idx < 0) return;
  const swapIdx = direction === "up" ? idx - 1 : idx + 1;
  if (swapIdx < 0 || swapIdx >= siblings.length) {
    ElMessage.warning("已在边界，无法移动。");
    return;
  }
  const other = siblings[swapIdx];
  try {
    await updateTaxonomyNode(tenantId.value, spaceId.value, row.id, {
      code: row.code,
      name: row.name,
      parent_id: row.parent_id,
      sort_order: other.sort_order
    });
    await updateTaxonomyNode(tenantId.value, spaceId.value, other.id, {
      code: other.code,
      name: other.name,
      parent_id: other.parent_id,
      sort_order: row.sort_order
    });
    ElMessage.success("已调整排序。");
    await loadNodes();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "排序失败");
  }
}

function onExternalPersist() {
  loadNodes();
}

function goFieldClassification() {
  router.push({ name: "dashboard-rule-taxonomy-field-classification" });
}

onMounted(() => {
  void loadTaxonomyLevels();
  window.addEventListener(TAXONOMY_NODE_PERSIST_EVENT, onExternalPersist);
  window.addEventListener(TAXONOMY_LEVEL_PERSIST_EVENT, onExternalPersist);
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onExternalPersist);
  if (ready.value) loadNodes();
});

onBeforeUnmount(() => {
  window.removeEventListener(TAXONOMY_NODE_PERSIST_EVENT, onExternalPersist);
  window.removeEventListener(TAXONOMY_LEVEL_PERSIST_EVENT, onExternalPersist);
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onExternalPersist);
});
</script>

<style scoped>
.txn {
  padding: 24px 28px 32px;
}

.txn__header {
  margin-bottom: 20px;
}

.txn__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.txn__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.txn__code {
  font-size: 0.8125rem;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--dsms-page-bg, #f4f6f9);
}

.txn__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.txn__table {
  width: 100%;
}

.txn__field-hint {
  margin: 6px 0 0;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}
</style>
