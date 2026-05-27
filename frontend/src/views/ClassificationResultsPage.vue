<template>
  <section class="clr dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="clr-title">
    <header class="clr__header">
      <h3 id="clr-title" class="clr__title">自动分类结果</h3>
      <p class="clr__lead">
        展示规则/矩阵求值后的字段<strong>密级</strong>与<strong>分类节点</strong>结果；可导出 CSV、查看操作审计。
      </p>
    </header>

    <el-tabs v-model="activeTab" class="clr__tabs">
      <el-tab-pane label="分类结果" name="results">
        <div class="clr__toolbar">
          <el-button type="primary" :loading="recomputing" @click="onRecompute">全量重算</el-button>
          <el-button @click="loadResults">刷新</el-button>
          <el-button :loading="exporting" @click="onExportCsv">导出 CSV</el-button>
          <el-button @click="goConfig">矩阵与规则配置</el-button>
        </div>

        <el-table
          v-loading="loading"
          class="clr__table"
          :data="resultRows"
          border
          stripe
          empty-text="暂无分类结果，请先配置规则/矩阵后点击「全量重算」"
        >
          <el-table-column prop="field_name" label="数据字段" min-width="180" show-overflow-tooltip />
          <el-table-column prop="sensitivity_level" label="密级" width="120" />
          <el-table-column label="分类节点" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              {{ taxonomyNodeLabel(row.taxonomy_node_id) }}
            </template>
          </el-table-column>
          <el-table-column label="来源" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_manual_override" type="warning" size="small">人工</el-tag>
              <el-tag v-else-if="row.matched_rule_id" type="info" size="small">规则</el-tag>
              <el-tag v-else-if="row.applied_matrix" type="success" size="small">矩阵</el-tag>
              <span v-else class="clr__muted">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新" width="168">
            <template #default="{ row }">
              {{ formatTime(row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openOverride(row)">人工覆写</el-button>
              <el-button link :disabled="!row.is_manual_override" @click="onRevert(row)">恢复自动</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="操作审计" name="audit">
        <div class="clr__toolbar">
          <dsms-filterable-select
            v-model="auditFilterKey"
            clearable
            placeholder="按行为筛选"
            class="clr__audit-filter"
            @change="onAuditFilterChange"
          >
            <el-option v-for="opt in auditBehaviorOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </dsms-filterable-select>
          <el-button @click="loadAudit">刷新</el-button>
        </div>

        <el-table
          v-loading="auditLoading"
          class="clr__table"
          :data="auditRows"
          border
          stripe
          empty-text="暂无审计记录"
        >
          <el-table-column prop="behavior_key" label="行为" min-width="180" show-overflow-tooltip />
          <el-table-column label="详情" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              {{ formatAuditDetail(row.detail_json) }}
            </template>
          </el-table-column>
          <el-table-column prop="user_id" label="操作人 ID" width="100" align="center" />
          <el-table-column label="时间" width="168">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>

        <div v-if="auditTotal > auditPageSize" class="clr__pager">
          <el-pagination
            v-model:current-page="auditPage"
            v-model:page-size="auditPageSize"
            :total="auditTotal"
            layout="total, prev, pager, next"
            @current-change="loadAudit"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </section>

  <el-dialog v-model="overrideVisible" title="人工覆写密级" width="440px" destroy-on-close>
    <el-form label-width="96px">
      <el-form-item label="数据字段">
        <span>{{ overrideRow?.field_name || "—" }}</span>
      </el-form-item>
      <el-form-item label="密级" required>
        <dsms-filterable-select v-model="overrideForm.sensitivity_level" placeholder="选择密级">
          <el-option v-for="g in gradeOptions" :key="g.label" :label="g.label" :value="g.label" />
        </dsms-filterable-select>
      </el-form-item>
      <el-form-item label="原因">
        <el-input v-model="overrideForm.reason" type="textarea" :rows="2" maxlength="500" show-word-limit />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="overrideVisible = false">取消</el-button>
      <el-button type="primary" :loading="overrideSaving" @click="submitOverride">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import DsmsFilterableSelect from "../components/DsmsFilterableSelect.vue";
import {
  classificationManualOverride,
  classificationRecompute,
  classificationRevertAuto,
  downloadClassificationExportCsv,
  fetchClassificationAudit,
  fetchClassificationResults,
  fetchSensitivityLevels
} from "../api/dsmsSpaceApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { getTaxonomyNodeById } from "../data/taxonomyNodeMock.js";
import { loadSensitivityLevels } from "../data/sensitivityLevelMock.js";

const AUDIT_BEHAVIOR_OPTIONS = [
  { value: "classification-matrix", label: "矩阵变更" },
  { value: "classification-matrix/delete", label: "矩阵删除" },
  { value: "classification-rules", label: "规则变更" },
  { value: "classification-rules/delete", label: "规则删除" },
  { value: "classification-recompute", label: "全量重算" },
  { value: "classification-manual-override", label: "人工覆写" },
  { value: "classification-revert-auto", label: "恢复自动" }
];

const { tenantId, spaceId, ready } = usePortalTenantContext();
const router = useRouter();
const activeTab = ref("results");
const loading = ref(false);
const exporting = ref(false);
const recomputing = ref(false);
const resultRows = ref([]);
const overrideVisible = ref(false);
const overrideSaving = ref(false);
const overrideRow = ref(null);
const overrideForm = reactive({ sensitivity_level: "", reason: "" });

const auditLoading = ref(false);
const auditRows = ref([]);
const auditTotal = ref(0);
const auditPage = ref(1);
const auditPageSize = ref(20);
const auditFilterKey = ref("");
const auditBehaviorOptions = AUDIT_BEHAVIOR_OPTIONS;

const gradeOptions = computed(() => loadSensitivityLevels());

function formatTime(iso) {
  if (!iso) return "—";
  return String(iso).slice(0, 16).replace("T", " ");
}

function taxonomyNodeLabel(nodeId) {
  if (!nodeId) return "—";
  const n = getTaxonomyNodeById(String(nodeId));
  return n ? `${n.name}（${n.code}）` : `节点 #${nodeId}`;
}

function formatAuditDetail(raw) {
  if (!raw) return "—";
  try {
    const obj = JSON.parse(raw);
    return JSON.stringify(obj);
  } catch {
    return String(raw);
  }
}

function parseDownloadFilename(contentDisposition, fallback) {
  if (!contentDisposition) return fallback;
  const m = /filename="([^"]+)"/i.exec(contentDisposition);
  return m?.[1] || fallback;
}

async function loadResults() {
  if (!tenantId.value) return;
  loading.value = true;
  try {
    const data = await fetchClassificationResults(tenantId.value, spaceId.value);
    resultRows.value = data?.items || [];
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载分类结果失败");
  } finally {
    loading.value = false;
  }
}

async function loadAudit() {
  if (!tenantId.value) return;
  auditLoading.value = true;
  try {
    const skip = (auditPage.value - 1) * auditPageSize.value;
    const data = await fetchClassificationAudit(
      tenantId.value,
      spaceId.value,
      skip,
      auditPageSize.value,
      auditFilterKey.value || null
    );
    auditRows.value = data?.items || [];
    auditTotal.value = data?.total ?? 0;
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载审计记录失败");
  } finally {
    auditLoading.value = false;
  }
}

function onAuditFilterChange() {
  auditPage.value = 1;
  loadAudit();
}

async function onExportCsv() {
  exporting.value = true;
  try {
    const res = await downloadClassificationExportCsv(tenantId.value, spaceId.value);
    const filename = parseDownloadFilename(
      res.headers?.["content-disposition"],
      "classification-results.csv"
    );
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("导出完成");
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "导出失败");
  } finally {
    exporting.value = false;
  }
}

async function onRecompute() {
  try {
    await ElMessageBox.confirm("将对空间内全部字段重新执行分类分级求值，是否继续？", "全量重算", {
      type: "warning",
      confirmButtonText: "重算",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  recomputing.value = true;
  try {
    const data = await classificationRecompute(tenantId.value, spaceId.value);
    ElMessage.success(`重算完成，更新 ${data?.updated_count ?? 0} 条。`);
    await loadResults();
    if (activeTab.value === "audit") await loadAudit();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "重算失败");
  } finally {
    recomputing.value = false;
  }
}

function openOverride(row) {
  overrideRow.value = row;
  overrideForm.sensitivity_level = row.sensitivity_level || "";
  overrideForm.reason = row.manual_reason || "";
  overrideVisible.value = true;
}

async function submitOverride() {
  if (!overrideForm.sensitivity_level.trim()) {
    ElMessage.warning("请选择密级。");
    return;
  }
  overrideSaving.value = true;
  try {
    await classificationManualOverride(tenantId.value, spaceId.value, overrideRow.value.id, {
      sensitivity_level: overrideForm.sensitivity_level.trim(),
      reason: overrideForm.reason.trim() || null
    });
    ElMessage.success("已保存人工覆写。");
    overrideVisible.value = false;
    await loadResults();
    if (activeTab.value === "audit") await loadAudit();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "保存失败");
  } finally {
    overrideSaving.value = false;
  }
}

async function onRevert(row) {
  try {
    await ElMessageBox.confirm("将清除人工标记并按规则重算该字段，是否继续？", "恢复自动", {
      type: "warning",
      confirmButtonText: "确定",
      cancelButtonText: "取消"
    });
  } catch {
    return;
  }
  try {
    await classificationRevertAuto(tenantId.value, spaceId.value, row.id);
    ElMessage.success("已恢复为自动分类结果。");
    await loadResults();
    if (activeTab.value === "audit") await loadAudit();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "操作失败");
  }
}

function goConfig() {
  router.push({ name: "dashboard-rule-taxonomy-classification-config" });
}

watch(activeTab, (tab) => {
  if (tab === "audit" && ready.value) loadAudit();
});

watch([ready, tenantId, spaceId], () => {
  if (ready.value) {
    fetchSensitivityLevels(tenantId.value, spaceId.value).catch(() => {});
    loadResults();
    if (activeTab.value === "audit") loadAudit();
  }
});

onMounted(() => {
  if (ready.value) {
    fetchSensitivityLevels(tenantId.value, spaceId.value).catch(() => {});
    loadResults();
  }
});
</script>

<style scoped>
.clr {
  padding: 24px 28px 32px;
}

.clr__header {
  margin-bottom: 16px;
}

.clr__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.clr__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.clr__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.clr__audit-filter {
  width: 220px;
}

.clr__table {
  width: 100%;
}

.clr__pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.clr__muted {
  color: var(--dsms-text-secondary);
  font-size: 0.8125rem;
}
</style>
