<template>
  <section class="dash-home dsms-glass-panel dsms-animate-stagger-0" aria-label="工作台首页">
    <header class="dash-home__header dsms-animate-stagger-1">
      <h2 class="dash-home__title">欢迎使用数据安全治理工作台</h2>
      <p class="dash-home__lead">
        当前工作台已对接后端 API；业务数据按所选<strong>项目 / 空间</strong>从服务端加载。
        请从下方快捷入口或左侧导航进入各模块。
      </p>
    </header>

    <div v-if="meReady" class="dash-home__grid dsms-animate-stagger-2">
      <article
        v-for="card in visibleCards"
        :key="card.key"
        class="dash-home__card"
        :class="{ 'dash-home__card--clickable': !!card.routeName }"
        role="region"
        :aria-label="card.title"
        @click="card.routeName && go(card.routeName)"
      >
        <div class="dash-home__card-head">
          <h3 class="dash-home__card-title">{{ card.title }}</h3>
          <el-badge v-if="card.badge != null && card.badge > 0" :value="card.badge" :max="99" />
        </div>
        <p class="dash-home__card-desc">{{ card.desc }}</p>
        <el-button v-if="card.routeName" type="primary" link class="dash-home__card-link" @click.stop="go(card.routeName)">
          进入 →
        </el-button>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { computeFoSubmissionReminderCount } from "../composables/useSubmissionTaskFoReminderCount";
import { ensurePortalTenantReady, usePortalTenantContext } from "../composables/usePortalTenantContext.js";
import {
  fetchMyFoBindings,
  fetchPendingApprovalCount,
  fetchSubmissionTasks,
  PORTAL_DATA_REFRESH_EVENT
} from "../api/portalApi.js";
import { foWorkflowProgressKey } from "../data/submissionFoWorkflowMock.js";
import { effectivePlatformRole, menuVisibilityForRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const router = useRouter();
const { tenantId, spaceId, ready } = usePortalTenantContext();
const { user: me, ready: meReady, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();

const platformRole = computed(() => effectivePlatformRole(me.value));
const menuVis = computed(() => menuVisibilityForRole(platformRole.value));
const isFunctionFo = computed(() => platformRole.value === PLATFORM_ROLE.FUNCTION_FO);
const isSecOrAdmin = computed(
  () => platformRole.value === PLATFORM_ROLE.SYSTEM_ADMIN || platformRole.value === PLATFORM_ROLE.SECURITY_FO
);

const foReminder = ref(0);
const approvalPending = ref(0);

async function refreshCounts() {
  if (!ready.value || !tenantId.value) {
    foReminder.value = computeFoSubmissionReminderCount(me.value);
    approvalPending.value = 0;
    return;
  }
  if (isSecOrAdmin.value) {
    try {
      approvalPending.value = await fetchPendingApprovalCount(tenantId.value, spaceId.value);
    } catch {
      approvalPending.value = 0;
    }
  } else {
    approvalPending.value = 0;
  }
  if (isFunctionFo.value) {
    try {
      const [binding, tasks] = await Promise.all([
        fetchMyFoBindings(tenantId.value, spaceId.value),
        fetchSubmissionTasks(tenantId.value, spaceId.value)
      ]);
      const bound = new Set(binding.function_keys || []);
      foReminder.value = tasks.filter((t) => {
        if (t.status !== "dispatched") return false;
        if (!bound.has(t.functionId)) return false;
        if (t.foCancellationRequested) return false;
        const k = foWorkflowProgressKey(t);
        return k === "not_started" || k === "relevance_draft" || k === "lifecycle_draft";
      }).length;
    } catch {
      foReminder.value = computeFoSubmissionReminderCount(me.value);
    }
  } else {
    foReminder.value = 0;
  }
}

const allCards = computed(() => [
  {
    key: "approval",
    title: "审批管理",
    desc: "处理业务功能绑定、字段变更、取消填报与填报内容审核等申请。",
    routeName: menuVis.value.approval ? "dashboard-approval" : null,
    badge: approvalPending.value,
    roles: [PLATFORM_ROLE.SECURITY_FO, PLATFORM_ROLE.SYSTEM_ADMIN, PLATFORM_ROLE.FUNCTION_FO]
  },
  {
    key: "submission-task",
    title: "填报任务管理",
    desc: "功能 FO 绑定业务功能、完成相关性判定与生命周期填报；数据安全 FO 下发与审核任务。",
    routeName: menuVis.value.submissionTask ? "dashboard-submission-task" : null,
    badge: foReminder.value,
    roles: [PLATFORM_ROLE.FUNCTION_FO, PLATFORM_ROLE.SECURITY_FO, PLATFORM_ROLE.SYSTEM_ADMIN]
  },
  {
    key: "field-catalog",
    title: "字段目录",
    desc: "维护数据字段定义；功能 FO 可申请新增或删除字段（需审批）。",
    routeName: menuVis.value.fieldCatalog ? "dashboard-field-catalog" : null,
    roles: [PLATFORM_ROLE.SECURITY_FO, PLATFORM_ROLE.SYSTEM_ADMIN, PLATFORM_ROLE.FUNCTION_FO]
  },
  {
    key: "rule-relevance",
    title: "功能数据安全相关性",
    desc: "配置相关性问卷与判定表达式，供功能 FO 填报时自动评估。",
    routeName: menuVis.value.ruleRelevance ? "dashboard-rule-relevance-questionnaire" : null,
    roles: [PLATFORM_ROLE.SECURITY_FO, PLATFORM_ROLE.SYSTEM_ADMIN]
  },
  {
    key: "rule-security",
    title: "安全要求",
    desc: "维护安全要求规则（富文本），用于治理识别与合规约束。",
    routeName: menuVis.value.ruleSecurity ? "dashboard-rule-security" : null,
    roles: [PLATFORM_ROLE.SECURITY_FO, PLATFORM_ROLE.SYSTEM_ADMIN]
  },
  {
    key: "document-resource",
    title: "文档资源",
    desc: "法规文件库与各模块 Excel 导入/导出、作业记录。",
    routeName: menuVis.value.documentResource ? "dashboard-document-resource" : null,
    roles: [PLATFORM_ROLE.SECURITY_FO, PLATFORM_ROLE.SYSTEM_ADMIN, PLATFORM_ROLE.FUNCTION_FO]
  },
  {
    key: "project",
    title: "项目管理",
    desc: "系统管理员创建、复制与管理租户项目；与顶栏项目切换共用 GET /api/v1/dsms/tenants。",
    routeName: menuVis.value.projectManagement ? "dashboard-project-management" : null,
    roles: [PLATFORM_ROLE.SYSTEM_ADMIN]
  }
]);

const visibleCards = computed(() =>
  allCards.value.filter((c) => c.routeName && c.roles.includes(platformRole.value))
);

function go(routeName) {
  router.push({ name: routeName });
}

onMounted(async () => {
  await Promise.all([ensureCurrentUser(), ensurePortalTenantReady()]);
  await refreshCounts();
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, refreshCounts);
});

onBeforeUnmount(() => {
  window.removeEventListener(PORTAL_DATA_REFRESH_EVENT, refreshCounts);
});
</script>

<style scoped>
.dash-home {
  padding: 32px 36px 40px;
}

.dash-home__header {
  margin-bottom: 28px;
}

.dash-home__title {
  margin: 0 0 12px;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.dash-home__lead {
  margin: 0;
  max-width: 52rem;
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--dsms-text-secondary);
}

.dash-home__loading {
  font-size: 0.875rem;
  color: var(--dsms-text-secondary);
}

.dash-home__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.dash-home__card {
  padding: 20px 22px;
  border-radius: 12px;
  border: 1px solid var(--dsms-glass-border-subtle, rgba(15, 23, 42, 0.08));
  background: var(--dsms-glass-surface, rgba(255, 255, 255, 0.55));
  transition: box-shadow 0.2s var(--dsms-ease-out, ease-out), transform 0.2s var(--dsms-ease-out, ease-out);
}

.dash-home__card--clickable {
  cursor: pointer;
}

@media (prefers-reduced-motion: no-preference) {
  .dash-home__card--clickable:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  }
}

.dash-home__card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.dash-home__card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.dash-home__card-desc {
  margin: 0 0 12px;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--dsms-text-secondary);
}

.dash-home__card-link {
  padding: 0;
  font-size: 0.8125rem;
}
</style>
