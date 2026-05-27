<template>
  <section class="clc dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="clc-title">
    <header class="clc__header">
      <h3 id="clc-title" class="clc__title">分类矩阵与规则</h3>
      <p class="clc__lead">
        配置<strong>分类矩阵</strong>（taxonomy_code → 密级）与<strong>分类规则</strong>（按字段属性匹配输出密级）。
        保存后请在「自动分类结果」页执行<strong>全量重算</strong>。
      </p>
    </header>

    <el-tabs v-model="activeTab" class="clc__tabs">
      <el-tab-pane label="分类矩阵" name="matrix">
        <div class="clc__toolbar">
          <el-button type="primary" @click="openMatrixCreate">新增矩阵</el-button>
          <el-button @click="loadMatrices">刷新</el-button>
          <el-button type="primary" plain @click="goResults">下一步：自动分类结果</el-button>
        </div>
        <el-table
          v-loading="matrixLoading"
          class="clc__table"
          :data="matrixRows"
          row-key="id"
          border
          stripe
          empty-text="暂无分类矩阵，请点击「新增矩阵」"
        >
          <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
          <el-table-column label="映射条目" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">
              {{ formatCellsPreview(row.cells_json) }}
            </template>
          </el-table-column>
          <el-table-column label="更新" width="168">
            <template #default="{ row }">
              {{ formatTime(row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openMatrixEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="onMatrixDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="分类规则" name="rules">
        <div class="clc__toolbar">
          <el-button type="primary" @click="openRuleCreate">新增规则</el-button>
          <el-button @click="loadRules">刷新</el-button>
        </div>
        <el-table
          v-loading="ruleLoading"
          class="clc__table"
          :data="ruleRows"
          row-key="id"
          border
          stripe
          empty-text="暂无分类规则，请点击「新增规则」"
        >
          <el-table-column prop="name" label="规则名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="priority" label="优先级" width="88" align="center" />
          <el-table-column label="匹配条件" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              {{ formatConditionPreview(row.condition_json) }}
            </template>
          </el-table-column>
          <el-table-column prop="output_sensitivity" label="输出密级" width="120" />
          <el-table-column label="启用" width="72" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? "是" : "否" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openRuleEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="onRuleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </section>

  <el-dialog
    v-model="matrixVisible"
    :title="matrixMode === 'create' ? '新增分类矩阵' : '编辑分类矩阵'"
    width="640px"
    destroy-on-close
    @closed="resetMatrixForm"
  >
    <el-form label-width="88px">
      <el-form-item label="名称" required>
        <el-input v-model="matrixForm.name" maxlength="100" show-word-limit />
      </el-form-item>
      <el-form-item label="说明">
        <el-input v-model="matrixForm.description" type="textarea" :rows="2" maxlength="500" show-word-limit />
      </el-form-item>
      <el-form-item label="映射">
        <div class="clc__cells">
          <div v-for="(cell, idx) in matrixForm.cells" :key="idx" class="clc__cell-row">
            <dsms-filterable-select v-model="cell.taxonomy_code" placeholder="分类 code" class="clc__cell-code">
              <el-option v-for="n in taxonomyNodeOptions" :key="n.code" :label="`${n.name}（${n.code}）`" :value="n.code" />
            </dsms-filterable-select>
            <dsms-filterable-select v-model="cell.sensitivity_level" placeholder="密级" class="clc__cell-level">
              <el-option v-for="g in gradeOptions" :key="g.label" :label="g.label" :value="g.label" />
            </dsms-filterable-select>
            <el-button link type="danger" @click="removeMatrixCell(idx)">移除</el-button>
          </div>
          <el-button link type="primary" @click="addMatrixCell">+ 添加映射</el-button>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="matrixVisible = false">取消</el-button>
      <el-button type="primary" :loading="matrixSaving" @click="submitMatrix">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="ruleVisible"
    :title="ruleMode === 'create' ? '新增分类规则' : '编辑分类规则'"
    width="520px"
    destroy-on-close
    @closed="resetRuleForm"
  >
    <el-form label-width="96px">
      <el-form-item label="规则名称" required>
        <el-input v-model="ruleForm.name" maxlength="100" show-word-limit />
      </el-form-item>
      <el-form-item label="优先级">
        <el-input-number v-model="ruleForm.priority" :min="1" :max="9999" />
        <p class="clc__hint">数值越小越先匹配。</p>
      </el-form-item>
      <el-form-item label="条件类型" required>
        <dsms-filterable-select v-model="ruleForm.conditionType" placeholder="选择条件类型">
          <el-option v-for="t in conditionTypes" :key="t.value" :label="t.label" :value="t.value" />
        </dsms-filterable-select>
      </el-form-item>
      <el-form-item v-if="ruleForm.conditionType !== 'default'" label="条件值" required>
        <el-input v-model="ruleForm.conditionValue" maxlength="200" show-word-limit />
      </el-form-item>
      <el-form-item label="输出密级" required>
        <dsms-filterable-select v-model="ruleForm.output_sensitivity" placeholder="选择密级">
          <el-option v-for="g in gradeOptions" :key="g.label" :label="g.label" :value="g.label" />
        </dsms-filterable-select>
      </el-form-item>
      <el-form-item label="启用">
        <el-switch v-model="ruleForm.is_active" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="ruleVisible = false">取消</el-button>
      <el-button type="primary" :loading="ruleSaving" @click="submitRule">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import {
  createClassificationMatrix,
  createClassificationRule,
  deleteClassificationMatrix,
  deleteClassificationRule,
  fetchClassificationMatrices,
  fetchClassificationRules,
  updateClassificationMatrix,
  updateClassificationRule
} from "../api/dsmsSpaceApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { loadSensitivityLevels } from "../data/sensitivityLevelMock.js";
import { loadTaxonomyNodes } from "../data/taxonomyNodeMock.js";

const CONDITION_TYPE_LABELS = {
  default: "默认（匹配全部字段）",
  identifier_contains: "标识符包含",
  field_name_contains: "字段名包含",
  data_type_equals: "数据类型等于"
};

const conditionTypes = Object.entries(CONDITION_TYPE_LABELS).map(([value, label]) => ({ value, label }));

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const activeTab = ref("matrix");
const matrixLoading = ref(false);
const ruleLoading = ref(false);
const matrixRows = ref([]);
const ruleRows = ref([]);
const matrixVisible = ref(false);
const ruleVisible = ref(false);
const matrixMode = ref("create");
const ruleMode = ref("create");
const matrixSaving = ref(false);
const ruleSaving = ref(false);

const matrixForm = reactive({
  id: null,
  name: "",
  description: "",
  cells: [{ taxonomy_code: "", sensitivity_level: "" }]
});

const ruleForm = reactive({
  id: null,
  name: "",
  priority: 100,
  conditionType: "default",
  conditionValue: "",
  output_sensitivity: "未分级",
  is_active: true
});

const gradeOptions = computed(() => loadSensitivityLevels());
const taxonomyNodeOptions = computed(() => loadTaxonomyNodes());

function formatTime(iso) {
  if (!iso) return "—";
  return String(iso).slice(0, 16).replace("T", " ");
}

function parseCellsJson(raw) {
  try {
    const arr = JSON.parse(raw || "[]");
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function parseConditionJson(raw) {
  try {
    return JSON.parse(raw || "{}");
  } catch {
    return {};
  }
}

function formatCellsPreview(raw) {
  const cells = parseCellsJson(raw);
  if (!cells.length) return "—";
  return cells
    .map((c) => `${c.taxonomy_code || "?"} → ${c.sensitivity_level || "?"}`)
    .join("；");
}

function formatConditionPreview(raw) {
  const cond = parseConditionJson(raw);
  const t = cond.type || "";
  const label = CONDITION_TYPE_LABELS[t] || t || "—";
  if (t === "default" || !cond.value) return label;
  return `${label}：${cond.value}`;
}

function buildConditionJson() {
  const body = { type: ruleForm.conditionType };
  if (ruleForm.conditionType !== "default") {
    body.value = ruleForm.conditionValue.trim();
  }
  return JSON.stringify(body);
}

function buildCellsJson() {
  const cells = matrixForm.cells
    .filter((c) => c.taxonomy_code && c.sensitivity_level)
    .map((c) => ({ taxonomy_code: c.taxonomy_code, sensitivity_level: c.sensitivity_level }));
  return JSON.stringify(cells);
}

async function loadMatrices() {
  if (!tenantId.value) return;
  matrixLoading.value = true;
  try {
    const data = await fetchClassificationMatrices(tenantId.value, spaceId.value);
    matrixRows.value = data?.items || [];
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载分类矩阵失败");
  } finally {
    matrixLoading.value = false;
  }
}

async function loadRules() {
  if (!tenantId.value) return;
  ruleLoading.value = true;
  try {
    const data = await fetchClassificationRules(tenantId.value, spaceId.value);
    ruleRows.value = data?.items || [];
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载分类规则失败");
  } finally {
    ruleLoading.value = false;
  }
}

function openMatrixCreate() {
  matrixMode.value = "create";
  resetMatrixForm();
  matrixVisible.value = true;
}

function openMatrixEdit(row) {
  matrixMode.value = "edit";
  matrixForm.id = row.id;
  matrixForm.name = row.name || "";
  matrixForm.description = row.description || "";
  const cells = parseCellsJson(row.cells_json);
  matrixForm.cells = cells.length
    ? cells.map((c) => ({
        taxonomy_code: c.taxonomy_code || "",
        sensitivity_level: c.sensitivity_level || ""
      }))
    : [{ taxonomy_code: "", sensitivity_level: "" }];
  matrixVisible.value = true;
}

function resetMatrixForm() {
  matrixForm.id = null;
  matrixForm.name = "";
  matrixForm.description = "";
  matrixForm.cells = [{ taxonomy_code: "", sensitivity_level: "" }];
}

function addMatrixCell() {
  matrixForm.cells.push({ taxonomy_code: "", sensitivity_level: "" });
}

function removeMatrixCell(idx) {
  if (matrixForm.cells.length <= 1) {
    matrixForm.cells[0] = { taxonomy_code: "", sensitivity_level: "" };
    return;
  }
  matrixForm.cells.splice(idx, 1);
}

async function submitMatrix() {
  if (!matrixForm.name.trim()) {
    ElMessage.warning("请填写矩阵名称。");
    return;
  }
  matrixSaving.value = true;
  try {
    const payload = {
      name: matrixForm.name.trim(),
      description: matrixForm.description.trim() || null,
      cells_json: buildCellsJson()
    };
    if (matrixMode.value === "create") {
      await createClassificationMatrix(tenantId.value, spaceId.value, payload);
      ElMessage.success("矩阵已创建。");
    } else {
      await updateClassificationMatrix(tenantId.value, spaceId.value, { id: matrixForm.id, ...payload });
      ElMessage.success("矩阵已更新。");
    }
    matrixVisible.value = false;
    await loadMatrices();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存矩阵失败");
  } finally {
    matrixSaving.value = false;
  }
}

async function onMatrixDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除矩阵「${row.name}」？`, "删除确认", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteClassificationMatrix(tenantId.value, spaceId.value, row.id);
    ElMessage.success("已删除。");
    await loadMatrices();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败");
  }
}

function openRuleCreate() {
  ruleMode.value = "create";
  resetRuleForm();
  ruleVisible.value = true;
}

function openRuleEdit(row) {
  ruleMode.value = "edit";
  ruleForm.id = row.id;
  ruleForm.name = row.name || "";
  ruleForm.priority = row.priority ?? 100;
  ruleForm.output_sensitivity = row.output_sensitivity || "未分级";
  ruleForm.is_active = row.is_active !== false;
  const cond = parseConditionJson(row.condition_json);
  ruleForm.conditionType = cond.type || "default";
  ruleForm.conditionValue = cond.value || "";
  ruleVisible.value = true;
}

function resetRuleForm() {
  ruleForm.id = null;
  ruleForm.name = "";
  ruleForm.priority = 100;
  ruleForm.conditionType = "default";
  ruleForm.conditionValue = "";
  ruleForm.output_sensitivity = "未分级";
  ruleForm.is_active = true;
}

async function submitRule() {
  if (!ruleForm.name.trim()) {
    ElMessage.warning("请填写规则名称。");
    return;
  }
  if (ruleForm.conditionType !== "default" && !ruleForm.conditionValue.trim()) {
    ElMessage.warning("请填写条件值。");
    return;
  }
  if (!ruleForm.output_sensitivity) {
    ElMessage.warning("请选择输出密级。");
    return;
  }
  ruleSaving.value = true;
  try {
    const payload = {
      name: ruleForm.name.trim(),
      priority: ruleForm.priority,
      condition_json: buildConditionJson(),
      output_sensitivity: ruleForm.output_sensitivity,
      is_active: ruleForm.is_active
    };
    if (ruleMode.value === "create") {
      await createClassificationRule(tenantId.value, spaceId.value, payload);
      ElMessage.success("规则已创建。");
    } else {
      await updateClassificationRule(tenantId.value, spaceId.value, { id: ruleForm.id, ...payload });
      ElMessage.success("规则已更新。");
    }
    ruleVisible.value = false;
    await loadRules();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存规则失败");
  } finally {
    ruleSaving.value = false;
  }
}

async function onRuleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除规则「${row.name}」？`, "删除确认", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteClassificationRule(tenantId.value, spaceId.value, row.id);
    ElMessage.success("已删除。");
    await loadRules();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败");
  }
}

function goResults() {
  router.push({ name: "dashboard-rule-taxonomy-classification-results" });
}

watch(
  ready,
  (v) => {
    if (v) {
      loadMatrices();
      loadRules();
    }
  },
  { immediate: true }
);

onMounted(() => {
  if (ready.value) {
    loadMatrices();
    loadRules();
  }
});
</script>

<style scoped>
.clc {
  padding: 20px 24px 24px;
}

.clc__header {
  margin-bottom: 16px;
}

.clc__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.clc__lead {
  margin: 0;
  max-width: 52rem;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.clc__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.clc__table {
  width: 100%;
}

.clc__cells {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.clc__cell-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.clc__cell-code {
  flex: 1 1 220px;
  min-width: 180px;
}

.clc__cell-level {
  flex: 0 1 140px;
  min-width: 120px;
}

.clc__hint {
  margin: 4px 0 0;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}
</style>
