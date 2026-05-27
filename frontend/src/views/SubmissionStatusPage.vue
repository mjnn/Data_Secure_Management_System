<template>
  <section class="sss dsms-glass-panel dsms-animate-stagger-0" aria-labelledby="sss-title">
    <header class="sss__header dsms-animate-stagger-1">
      <h2 id="sss-title" class="sss__title">填报情况</h2>
      <p class="sss__lead">
        汇总当前项目下各<strong>业务功能</strong>与<strong>填报任务</strong>的状态；数据来自后端任务与业务功能接口，统计口径与「填报任务管理」一致。
      </p>
    </header>

    <template v-if="meReady && isSecOrAdmin">
      <el-row :gutter="12" class="sss__stats dsms-animate-stagger-2">
        <el-col v-for="card in statCards" :key="card.key" :xs="24" :sm="12" :md="8" :lg="4">
          <el-card shadow="hover" class="sss__stat-card">
            <div class="sss__stat-title">{{ card.title }}</div>
            <div class="sss__stat-value">{{ card.value }}</div>
            <div class="sss__stat-hint">{{ card.hint }}</div>
          </el-card>
        </el-col>
      </el-row>

      <div class="sss__chart-toolbar dsms-animate-stagger-3">
        <span class="sss__chart-label">图表类型</span>
        <el-radio-group v-model="chartType" size="small" aria-label="选择图表类型">
          <el-radio-button value="pie">饼图</el-radio-button>
          <el-radio-button value="bar">柱状图</el-radio-button>
        </el-radio-group>
      </div>
      <div ref="chartRef" class="sss__chart" role="img" aria-label="填报情况统计图" />

      <h3 class="sss__h3">填报任务明细</h3>
      <p class="sss__sub">当前全部任务行；任务状态、填报与审核列由 API 数据推导。</p>
      <el-table class="sss__table" :data="taskRows" row-key="id" border stripe size="small">
        <el-table-column prop="id" label="ID" width="64" align="center" />
        <el-table-column label="业务功能" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.functionName }}</template>
        </el-table-column>
        <el-table-column prop="title" label="任务名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="任务状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.taskStatus === '已下发' ? 'success' : 'info'" size="small">{{ row.taskStatus }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="填报进度" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.fillTag" size="small">{{ row.fillLabel }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="120" align="center">
          <template #default="{ row }">
            <span>{{ row.auditLabel }}</span>
          </template>
        </el-table-column>
        <el-table-column label="看板归类" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.bucketLabel }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </section>
</template>

<script setup>
import * as echarts from "echarts";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import { useRouter } from "vue-router";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { submissionFunctionName } from "../data/submissionTasksMock";
import { ensurePortalTenantReady, usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import {
  fetchBusinessFunctions,
  fetchSubmissionTasks,
  PORTAL_DATA_REFRESH_EVENT
} from "../api/portalApi.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";
import { ElMessage } from "element-plus";

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const { user: me, ready: meReady, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();
const tasks = ref([]);
const functions = ref([]);
const chartRef = ref(null);
const chartType = ref("pie");
const chartInstance = shallowRef(null);
const chartResizeObserver = ref(null);

const isSecOrAdmin = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

async function reloadTasks() {
  if (!ready.value || !tenantId.value) return;
  try {
    const [fnList, taskList] = await Promise.all([
      fetchBusinessFunctions(tenantId.value, spaceId.value),
      fetchSubmissionTasks(tenantId.value, spaceId.value)
    ]);
    functions.value = fnList;
    tasks.value = taskList;
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "加载填报情况失败");
  }
}

function computeDashboardStats(tlist, functions) {
  const unboundFo = functions.filter((f) => !f.functionFoBound).length;
  const boundFns = functions.filter((f) => f.functionFoBound);
  let noTaskFn = 0;
  for (const f of boundFns) {
    if (!tlist.some((t) => t.functionId === f.id)) noTaskFn += 1;
  }
  let notDispatched = 0;
  let fillIncomplete = 0;
  let filledPendingAudit = 0;
  let auditDone = 0;
  for (const t of tlist) {
    if (t.status === "draft") {
      notDispatched += 1;
      continue;
    }
    if (t.status !== "dispatched") continue;
    const fillDone = !t.foCancellationRequested && t.foFillStatus === "submitted";
    if (!fillDone) {
      fillIncomplete += 1;
      continue;
    }
    if (t.auditStatus === "approved") auditDone += 1;
    else filledPendingAudit += 1;
  }
  return { unboundFo, noTaskFn, notDispatched, fillIncomplete, filledPendingAudit, auditDone };
}

const stats = computed(() => computeDashboardStats(tasks.value, functions.value));

const statCards = computed(() => {
  const s = stats.value;
  return [
    { key: "unbound", title: "未绑定 FO", value: s.unboundFo, hint: "业务功能项" },
    { key: "noTask", title: "未创建任务", value: s.noTaskFn, hint: "已绑 FO 但无任务" },
    { key: "notDispatched", title: "未下发任务", value: s.notDispatched, hint: "草稿任务数" },
    { key: "fillInc", title: "填报未完成", value: s.fillIncomplete, hint: "已下发未提交" },
    { key: "pendAudit", title: "填报完成未审核", value: s.filledPendingAudit, hint: "已提交待审" },
    { key: "auditOk", title: "填报审核完成", value: s.auditDone, hint: "审核通过" }
  ];
});

const CHART_COLORS = ["#909399", "#409eff", "#e6a23c", "#f56c6c", "#b88230", "#67c23a"];

const chartSeriesData = computed(() => {
  const s = stats.value;
  return [
    { name: "未绑定FO", value: s.unboundFo, itemStyle: { color: CHART_COLORS[0] } },
    { name: "未创建任务", value: s.noTaskFn, itemStyle: { color: CHART_COLORS[1] } },
    { name: "未下发任务", value: s.notDispatched, itemStyle: { color: CHART_COLORS[2] } },
    { name: "填报未完成", value: s.fillIncomplete, itemStyle: { color: CHART_COLORS[3] } },
    { name: "填报完成未审核", value: s.filledPendingAudit, itemStyle: { color: CHART_COLORS[4] } },
    { name: "填报审核完成", value: s.auditDone, itemStyle: { color: CHART_COLORS[5] } }
  ];
});

function taskBucketAndLabels(t, fnList) {
  const fn = fnList.find((f) => f.id === t.functionId);
  if (fn && !fn.functionFoBound) {
    return {
      bucketLabel: "未绑定FO（该功能无绑定功能 FO）",
      fillLabel: "—",
      fillTag: "info",
      auditLabel: "—"
    };
  }
  if (t.status === "draft") {
    return {
      bucketLabel: "未下发任务",
      fillLabel: "—",
      fillTag: "info",
      auditLabel: "—"
    };
  }
  if (t.status === "dispatched") {
    if (t.foCancellationRequested) {
      return {
        bucketLabel: "填报未完成（取消申请中）",
        fillLabel: "取消申请中",
        fillTag: "warning",
        auditLabel: "—"
      };
    }
    if (t.foFillStatus === "not_started") {
      return { bucketLabel: "填报未完成", fillLabel: "未填报", fillTag: "info", auditLabel: "—" };
    }
    if (t.foFillStatus === "draft") {
      return { bucketLabel: "填报未完成", fillLabel: "草稿", fillTag: "warning", auditLabel: "—" };
    }
    if (t.foFillStatus === "submitted") {
      if (t.auditStatus === "approved") {
        return { bucketLabel: "填报审核完成", fillLabel: "已提交", fillTag: "success", auditLabel: "已通过" };
      }
      if (t.auditStatus === "returned") {
        return { bucketLabel: "填报完成未审核", fillLabel: "已提交", fillTag: "success", auditLabel: "已退回" };
      }
      return { bucketLabel: "填报完成未审核", fillLabel: "已提交", fillTag: "success", auditLabel: "待审核" };
    }
  }
  return { bucketLabel: "其它", fillLabel: "—", fillTag: "info", auditLabel: "—" };
}

const taskRows = computed(() =>
  [...tasks.value]
    .sort((a, b) => b.id - a.id)
    .map((t) => {
      const extra = taskBucketAndLabels(t, functions.value);
      return {
        id: t.id,
        functionName: submissionFunctionName(t.functionId),
        title: t.title,
        taskStatus: t.status === "dispatched" ? "已下发" : "草稿",
        ...extra
      };
    })
);

function applyChartOption() {
  const el = chartRef.value;
  if (!el) return;
  if (!chartInstance.value) {
    chartInstance.value = echarts.init(el);
  }
  const data = chartSeriesData.value;
  const textColor = getComputedStyle(document.documentElement).getPropertyValue("--dsms-text").trim() || "#303133";
  const subColor = getComputedStyle(document.documentElement).getPropertyValue("--dsms-text-secondary").trim() || "#606266";

  if (chartType.value === "pie") {
    chartInstance.value.setOption(
      {
        color: CHART_COLORS,
        tooltip: { trigger: "item", formatter: "{b}：{c}（{d}%）" },
        legend: { bottom: 0, textStyle: { color: subColor } },
        series: [
          {
            type: "pie",
            radius: ["36%", "68%"],
            avoidLabelOverlap: true,
            itemStyle: { borderRadius: 4, borderColor: "#fff", borderWidth: 1 },
            label: { color: textColor },
            data
          }
        ]
      },
      true
    );
  } else {
    chartInstance.value.setOption(
      {
        color: CHART_COLORS,
        tooltip: { trigger: "axis" },
        grid: { left: 48, right: 24, top: 32, bottom: 80 },
        xAxis: {
          type: "category",
          data: data.map((d) => d.name),
          axisLabel: { color: subColor, rotate: 28, interval: 0, fontSize: 11 }
        },
        yAxis: { type: "value", minInterval: 1, axisLabel: { color: subColor }, splitLine: { lineStyle: { type: "dashed" } } },
        series: [{ type: "bar", data: data.map((d) => ({ value: d.value, itemStyle: d.itemStyle })), barMaxWidth: 48 }]
      },
      true
    );
  }
}

function resizeChart() {
  chartInstance.value?.resize();
}

function goDetail(id) {
  router.push({ name: "dashboard-submission-task-detail", params: { taskId: String(id) } });
}

onMounted(async () => {
  await Promise.all([ensureCurrentUser(), ensurePortalTenantReady()]);
  const role = effectivePlatformRole(me.value);
  if (role !== PLATFORM_ROLE.SYSTEM_ADMIN && role !== PLATFORM_ROLE.SECURITY_FO) {
    ElMessage.warning("当前角色无权访问填报情况。");
    await router.replace({ name: "dashboard-home" });
    return;
  }
  await reloadTasks();
  await nextTick();
  applyChartOption();
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, reloadTasks);
  window.addEventListener("resize", resizeChart);
  if (chartRef.value && typeof ResizeObserver !== "undefined") {
    const ro = new ResizeObserver(() => resizeChart());
    ro.observe(chartRef.value);
    chartResizeObserver.value = ro;
  }
});

watch([chartType, chartSeriesData], () => {
  nextTick(() => applyChartOption());
});

watch(tasks, () => {
  nextTick(() => applyChartOption());
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, reloadTasks);
  window.removeEventListener("resize", resizeChart);
  chartResizeObserver.value?.disconnect();
  chartResizeObserver.value = null;
  chartInstance.value?.dispose();
  chartInstance.value = null;
});
</script>

<style scoped>
.sss {
  padding: 24px 28px 32px;
}

.sss__header {
  margin-bottom: 20px;
}

.sss__title {
  margin: 0 0 8px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.sss__lead {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.sss__code {
  padding: 1px 6px;
  font-size: 0.8125rem;
  border-radius: 4px;
  background: var(--dsms-fill-light, #f5f7fa);
  color: var(--dsms-text);
}

.sss__stats {
  margin-bottom: 16px;
}

.sss__stat-card :deep(.el-card__body) {
  padding: 14px 16px;
}

.sss__stat-title {
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
  margin-bottom: 6px;
}

.sss__stat-value {
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--dsms-text);
  line-height: 1.2;
}

.sss__stat-hint {
  margin-top: 6px;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}

.sss__chart-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.sss__chart-label {
  font-size: 0.875rem;
  color: var(--dsms-text-secondary);
}

.sss__chart {
  width: 100%;
  height: 360px;
  margin-bottom: 24px;
}

.sss__h3 {
  margin: 0 0 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.sss__sub {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--dsms-text-secondary);
}

.sss__table {
  width: 100%;
}
</style>
