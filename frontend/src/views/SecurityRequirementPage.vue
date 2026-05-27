<template>
  <section class="srq dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="srq-title">
    <header class="srq__header">
      <h2 id="srq-title" class="srq__title">安全要求</h2>
      <p class="srq__lead">
        数据字段的<strong>分类</strong>（「数据分类标准」）与<strong>密级</strong>（「密级绑定」）已在前序步骤完成；本页仅根据字段的
        <strong>密级</strong>、<strong>分类</strong>（树路径以 <code class="srq__code">-</code> 连接）及<strong>其他生命周期元字段取值</strong>
        配置触发规则并<strong>求值</strong>：条件成立时执行下方配置的<strong>安全要求正文</strong>（暂为富文本占位，具体检查项联调待定）。
      </p>
    </header>

    <div class="srq__toolbar">
      <el-button type="primary" @click="openCreate">新增规则</el-button>
    </div>

    <el-table class="srq__table" :data="ruleRows" row-key="id" border stripe empty-text="暂无规则，请点击「新增规则」">
      <el-table-column prop="rule_name" label="规则名称" min-width="160" show-overflow-tooltip />
      <el-table-column label="触发条件" min-width="280" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.triggerPreview }}
        </template>
      </el-table-column>
      <el-table-column label="执行的安全要求" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.actionPreview }}
        </template>
      </el-table-column>
      <el-table-column prop="updatedAt" label="更新" width="108" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-card class="srq__card" shadow="never">
      <template #header>
        <span class="srq__card-title">按数据字段求值</span>
      </template>
      <p class="srq__hint">
        选择数据字段后，读取其已配置的<strong>密级 / 分类</strong>（及生命周期取值，若有），对<strong>全部规则</strong>试算是否触发。
      </p>
      <p v-if="trialSnapshot" class="srq__snapshot">
        当前字段：<strong>密级</strong> {{ trialSnapshot.gradeLabel }} · <strong>分类</strong> {{ trialSnapshot.taxPath }}
      </p>
      <div class="srq__trial-bar">
        <dsms-filterable-select
          v-model="trialFieldId"
          class="srq__trial-select"
          placeholder="选择数据字段"
          aria-label="试算字段"
        >
          <el-option v-for="f in fieldOptions" :key="f.id" :label="f.label" :value="f.id" />
        </dsms-filterable-select>
      </div>
      <el-table
        v-if="trialFieldId && trialResults.length"
        :data="trialResults"
        border
        stripe
        size="small"
        class="srq__trial-table"
      >
        <el-table-column prop="rule.rule_name" label="规则" min-width="140" show-overflow-tooltip />
        <el-table-column label="是否触发" width="96" align="center">
          <template #default="{ row }">
            <el-tag :type="row.triggered ? 'success' : 'info'" size="small">
              {{ row.triggered ? "触发" : "未触发" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actionPreview" label="将执行" min-width="160" show-overflow-tooltip />
        <el-table-column prop="evalHint" label="说明" min-width="220" show-overflow-tooltip />
      </el-table>
      <el-empty v-else-if="trialFieldId" description="暂无规则" :image-size="64" />
    </el-card>
  </section>

  <el-dialog
    v-model="editVisible"
    class="srq-edit-dialog"
    :title="editMode === 'create' ? '新增安全要求规则' : '编辑安全要求规则'"
    width="720px"
    append-to-body
    align-center
    destroy-on-close
    @closed="resetEdit"
  >
    <el-form label-width="120px" class="srq__form">
      <el-form-item label="规则名称" required>
        <el-input v-model="editForm.rule_name" maxlength="128" show-word-limit placeholder="便于识别的规则名称" />
      </el-form-item>

      <el-form-item label="触发条件" required>
        <p class="srq__form-hint">
          仅描述密级 / 分类 / 生命周期取值组合；对具体字段求值时在列表下方选择数据字段。
        </p>
        <SecurityLogicExprBuilder :group="editForm.trigger_root" />
      </el-form-item>

      <el-form-item label="执行的安全要求">
        <p class="srq__form-hint">暂以富文本录入说明性要求；结构化检查（如最低密级）留待后续联调。</p>
        <dsms-rich-text-editor v-model="editForm.action.content_html" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible = false">取消</el-button>
      <el-button type="primary" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import DsmsRichTextEditor from "../components/DsmsRichTextEditor.vue";
import SecurityLogicExprBuilder from "../components/security/SecurityLogicExprBuilder.vue";
import {
  createSecurityRequirementRule,
  deleteSecurityRequirementRule,
  fetchSecurityRequirements,
  updateSecurityRequirementRule
} from "../api/dsmsSpaceApi.js";
import { fetchFieldCatalog, PORTAL_DATA_REFRESH_EVENT } from "../api/portalApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { describeFieldGovernanceSnapshot } from "../data/securityConditionCatalog.js";
import { loadDataFieldCatalogEntries } from "../data/dataFieldCatalogMock.js";
import { newTriggerGroupNode } from "../data/securityLogicTree.js";
import {
  evaluateRulesForField,
  formatRuleActionPreview,
  formatRuleTriggerPreview,
  loadSecurityRequirementRules,
  validateSecurityRule
} from "../data/securityRequirementRulesMock.js";

const { tenantId, spaceId, ready } = usePortalTenantContext();
const refreshTick = ref(0);
const trialFieldId = ref("");
const editVisible = ref(false);
const editMode = ref("create");
const editingId = ref("");

const fieldOptions = computed(() => {
  void refreshTick.value;
  return loadDataFieldCatalogEntries()
    .map((f) => ({ id: f.id, label: String(f.label || "").trim() || f.id }))
    .sort((a, b) => a.label.localeCompare(b.label, "zh-Hans-CN"));
});

const trialSnapshot = computed(() => {
  void refreshTick.value;
  if (!trialFieldId.value) return null;
  return describeFieldGovernanceSnapshot(trialFieldId.value);
});

const ruleRows = computed(() => {
  void refreshTick.value;
  return loadSecurityRequirementRules().map((r) => ({
    ...r,
    triggerPreview: formatRuleTriggerPreview(r),
    actionPreview: formatRuleActionPreview(r)
  }));
});

const trialResults = computed(() => {
  void refreshTick.value;
  if (!trialFieldId.value) return [];
  return evaluateRulesForField(trialFieldId.value);
});

const editForm = reactive({
  rule_name: "",
  trigger_root: newTriggerGroupNode(),
  action: { content_html: "", is_active: true }
});

function bumpLocal() {
  refreshTick.value++;
}

async function reloadRules() {
  if (!tenantId.value) return;
  try {
    await Promise.all([
      fetchFieldCatalog(tenantId.value, spaceId.value),
      fetchSecurityRequirements(tenantId.value, spaceId.value)
    ]);
    bumpLocal();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载安全要求失败");
  }
}

watch([ready, tenantId, spaceId], () => {
  if (ready.value) reloadRules();
});

function anchorFieldId() {
  const cat = loadDataFieldCatalogEntries();
  const row = cat[0];
  return row?._apiId || row?.id || null;
}

function resetEditForm() {
  editForm.rule_name = "";
  editForm.trigger_root = newTriggerGroupNode();
  editForm.action = { content_html: "", is_active: true };
}

function openCreate() {
  editMode.value = "create";
  editingId.value = "";
  resetEditForm();
  editVisible.value = true;
}

function openEdit(row) {
  editMode.value = "edit";
  editingId.value = row.id;
  editForm.rule_name = row.rule_name;
  editForm.trigger_root = JSON.parse(JSON.stringify(row.trigger_root));
  editForm.action = JSON.parse(JSON.stringify(row.action));
  editVisible.value = true;
}

function resetEdit() {
  resetEditForm();
}

async function submitEdit() {
  const payload = {
    rule_name: editForm.rule_name,
    trigger_root: editForm.trigger_root,
    action: editForm.action
  };
  const check = validateSecurityRule(payload);
  if (!check.ok) {
    ElMessage.error(check.message);
    return;
  }
  const anchor = anchorFieldId();
  if (!anchor) {
    ElMessage.error("请先在「数据字段」中维护至少一条主表字段。");
    return;
  }
  try {
    if (editMode.value === "create") {
      await createSecurityRequirementRule(tenantId.value, spaceId.value, payload, anchor);
      ElMessage.success("已新增规则。");
    } else {
      await updateSecurityRequirementRule(tenantId.value, spaceId.value, editingId.value, payload);
      ElMessage.success("已保存规则。");
    }
    editVisible.value = false;
    await reloadRules();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除规则「${row.rule_name}」吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  try {
    await deleteSecurityRequirementRule(tenantId.value, spaceId.value, row.id);
    ElMessage.success("已删除规则。");
    await reloadRules();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败");
  }
}

function onExternalPersist() {
  reloadRules();
}

onMounted(() => {
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onExternalPersist);
  if (ready.value) reloadRules();
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onExternalPersist);
});
</script>

<style scoped>
.srq {
  padding: 24px 28px 32px;
}

.srq__header {
  margin-bottom: 16px;
}

.srq__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.srq__lead {
  margin: 0;
  max-width: 52rem;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.srq__code {
  font-size: 0.8125rem;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--dsms-page-bg, #f4f6f9);
}

.srq__toolbar {
  margin-bottom: 12px;
}

.srq__table {
  width: 100%;
  margin-bottom: 20px;
}

.srq__card {
  border: 1px solid var(--el-border-color, #dcdfe6);
}

.srq__card-title {
  font-weight: 600;
  color: var(--dsms-text);
}

.srq__hint {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  color: var(--dsms-text-secondary);
}

.srq__snapshot {
  margin: 0 0 12px;
  padding: 8px 12px;
  font-size: 0.8125rem;
  border-radius: 8px;
  background: var(--dsms-page-bg, #f4f6f9);
  color: var(--dsms-text-secondary);
}

.srq__trial-bar {
  margin-bottom: 12px;
}

.srq__trial-select {
  width: 100%;
  max-width: 360px;
}

.srq__trial-table {
  width: 100%;
}

.srq__form-hint {
  margin: 0 0 8px;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}
</style>
