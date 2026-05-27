<template>
  <section class="cgl dsms-glass-panel dsms-animate-stagger-1" aria-labelledby="cgl-title">
    <header class="cgl__header">
      <h3 id="cgl-title" class="cgl__title">密级定义</h3>
      <p class="cgl__lead">
        注册本空间可使用的<strong>密级标签</strong>（<code class="cgl__code">code</code> / 名称）；「数据字段绑定」中的
        <code class="cgl__code">grade_label</code> 须与名称一致。数据来自后端 <code class="cgl__code">/sensitivity-levels</code>（只读，维护请使用 Excel 导入）。
      </p>
    </header>

    <div class="cgl__toolbar">
      <el-button type="primary" plain @click="goBindings">下一步：数据字段绑定</el-button>
      <el-button @click="reloadLevels">刷新</el-button>
    </div>

    <el-table
      class="cgl__table"
      :data="levelRows"
      row-key="id"
      border
      stripe
      empty-text="暂无密级定义，请点击「新增密级」"
    >
      <el-table-column prop="sort_order" label="排序" width="72" align="center" />
      <el-table-column prop="label" label="密级名称" min-width="120" show-overflow-tooltip />
      <el-table-column prop="code" label="code" width="140" show-overflow-tooltip />
      <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
      <el-table-column label="已绑定字段数" width="120" align="center">
        <template #default="{ row }">
          {{ bindingCount(row.label) }}
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { fetchFieldClassGrades, fetchSensitivityLevels } from "../api/dsmsSpaceApi.js";
import { PORTAL_DATA_REFRESH_EVENT } from "../api/portalApi.js";
import { usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import { countFieldBindingsByGradeLabel } from "../data/fieldClassGradeBindingMock.js";
import { loadSensitivityLevels } from "../data/sensitivityLevelMock.js";

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const refreshTick = ref(0);

const levelRows = computed(() => {
  void refreshTick.value;
  return loadSensitivityLevels();
});

function bindingCount(label) {
  return countFieldBindingsByGradeLabel(label);
}

function bumpLocal() {
  refreshTick.value++;
}

async function reloadLevels() {
  if (!tenantId.value) return;
  try {
    await Promise.all([
      fetchSensitivityLevels(tenantId.value, spaceId.value),
      fetchFieldClassGrades(tenantId.value, spaceId.value)
    ]);
    bumpLocal();
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载密级失败");
  }
}

watch([ready, tenantId, spaceId], () => {
  if (ready.value) reloadLevels();
});

function goBindings() {
  router.push({ name: "dashboard-rule-classification-bindings" });
}

function onLevelsPersist() {
  reloadLevels();
}

onMounted(() => {
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, onLevelsPersist);
  if (ready.value) reloadLevels();
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, onLevelsPersist);
});
</script>

<style scoped>
.cgl {
  padding: 24px 28px 32px;
}

.cgl__header {
  margin-bottom: 20px;
}

.cgl__title {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.cgl__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.cgl__code {
  font-size: 0.8125rem;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--dsms-page-bg, #f4f6f9);
}

.cgl__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.cgl__table {
  width: 100%;
}

.cgl__field-hint {
  margin: 6px 0 0;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}
</style>
