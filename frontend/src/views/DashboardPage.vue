<template>
  <div class="dsms-dashboard-page">
    <header class="dsms-portal-topbar">
      <div class="dsms-portal-topbar__brand">
        <PortalBrandLogo />
        <h1 class="dsms-portal-title">上汽大众研发数据安全治理工作台</h1>
      </div>
      <div class="dsms-portal-topbar__actions">
        <el-dropdown
          ref="tenantDropdownRef"
          trigger="click"
          placement="bottom-end"
          @command="onTenantCommand"
        >
          <el-button
            plain
            size="small"
            :title="currentTenantLabel"
            :aria-label="tenantMenuAriaLabel"
          >
            <span class="tenant-name">{{ currentTenantLabel }}</span>
            <span class="tenant-caret" aria-hidden="true">▾</span>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="switch">项目切换</el-dropdown-item>
              <el-dropdown-item v-if="canAccessProjectManagement" command="manage">项目管理</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown trigger="click" placement="bottom-end" @command="onUserCommand">
          <button
            type="button"
            class="user-trigger"
            :aria-label="userAriaLabel"
          >
            <span class="user-avatar" aria-hidden="true">{{ userAvatarText }}</span>
            <span class="user-name">{{ userDisplayName }}</span>
            <span class="user-caret" aria-hidden="true">▾</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="account">账号设置</el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <ThemeToggleControl />
      </div>
    </header>

    <!-- 显式 horizontal：避免 EP 根据子节点推断 is-vertical 时误判，侧栏与主区被纵向堆叠 -->
    <el-container class="dashboard-body" direction="horizontal">
      <el-aside class="dashboard-aside" :width="asideWidth">
        <div class="aside-toolbar" :class="{ 'aside-toolbar--collapsed': asideCollapsed }">
          <el-button
            circle
            text
            type="primary"
            class="aside-collapse-btn"
            :aria-label="asideCollapsed ? '展开侧边栏' : '折叠侧边栏'"
            :title="asideCollapsed ? '展开' : '折叠'"
            @click="toggleAside"
          >
            <el-icon :size="18">
              <Expand v-if="asideCollapsed" />
              <Fold v-else />
            </el-icon>
          </el-button>
        </div>
        <nav class="aside-nav" aria-label="主导航">
          <el-menu
            class="dashboard-menu"
            :class="{ 'dashboard-menu--suppress-labels': suppressMenuLabels }"
            :default-active="activeMenu"
            :collapse="asideCollapsed"
            :collapse-transition="true"
            :background-color="menuBackgroundColor"
            :text-color="menuTextColor"
            :active-text-color="menuActiveTextColor"
            @select="onMenuSelect"
          >
            <el-menu-item v-if="menuVis.home" index="home">
              <el-icon><House /></el-icon>
              <span>首页</span>
            </el-menu-item>
            <el-menu-item v-if="menuVis.userManagement" index="user-management">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
            <el-menu-item v-if="menuVis.projectManagement" index="project-management">
              <el-icon><OfficeBuilding /></el-icon>
              <span>项目管理</span>
            </el-menu-item>
            <el-sub-menu v-if="menuVis.submissionParent" index="submission">
              <template #title>
                <el-icon><EditPen /></el-icon>
                <span>填报管理</span>
              </template>
              <el-menu-item v-if="menuVis.submissionStatus" index="submission-status">
                <el-icon><DataLine /></el-icon>
                <span>填报情况</span>
              </el-menu-item>
              <el-menu-item
                v-if="menuVis.submissionTask"
                index="submission-task"
                class="dashboard-menu-item--with-badge"
              >
                <el-icon><Calendar /></el-icon>
                <span>填报任务管理</span>
                <el-badge
                  v-if="foSubmissionReminderCount > 0 && isFunctionFoRole"
                  class="dashboard-menu-item__badge"
                  :value="foSubmissionReminderCount"
                  :max="99"
                />
              </el-menu-item>
            </el-sub-menu>
            <el-sub-menu v-if="menuVis.fieldParent" index="field-governance">
              <template #title>
                <el-icon><Grid /></el-icon>
                <span>字段管理</span>
              </template>
              <el-menu-item v-if="menuVis.fieldLifecycle" index="field-lifecycle-meta">
                <el-icon><Cpu /></el-icon>
                <span>数据安全生命周期元字段</span>
              </el-menu-item>
              <el-menu-item v-if="menuVis.fieldCatalog" index="field-catalog">
                <el-icon><Document /></el-icon>
                <span>数据字段</span>
              </el-menu-item>
            </el-sub-menu>
            <el-sub-menu v-if="menuVis.ruleGovernance" index="rule-governance">
              <template #title>
                <el-icon><Setting /></el-icon>
                <span>规则管理</span>
              </template>
              <el-menu-item v-if="menuVis.ruleRelevance" index="rule-relevance">
                <el-icon><Connection /></el-icon>
                <span>功能数据安全相关性</span>
              </el-menu-item>
              <el-menu-item v-if="menuVis.ruleTaxonomy" index="rule-taxonomy">
                <el-icon><Share /></el-icon>
                <span>数据分类标准</span>
              </el-menu-item>
              <el-menu-item v-if="menuVis.ruleClassification" index="rule-classification">
                <el-icon><Lock /></el-icon>
                <span>密级绑定</span>
              </el-menu-item>
              <el-menu-item v-if="menuVis.ruleSecurity" index="rule-security">
                <el-icon><WarningFilled /></el-icon>
                <span>安全要求</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-if="menuVis.documentResource" index="document-resource">
              <el-icon><FolderOpened /></el-icon>
              <span>文档资源</span>
            </el-menu-item>
            <el-menu-item
              v-if="menuVis.approval"
              index="approval"
              :class="{ 'dashboard-menu-item--with-badge': isSecOrAdminRole && approvalPendingCount > 0 }"
            >
              <el-icon><CircleCheck /></el-icon>
              <span>审批管理</span>
              <el-badge
                v-if="isSecOrAdminRole && approvalPendingCount > 0"
                class="dashboard-menu-item__badge"
                :value="approvalPendingCount"
                :max="99"
              />
            </el-menu-item>
          </el-menu>
        </nav>
      </el-aside>

      <el-main class="dashboard-main">
        <router-view />
      </el-main>
    </el-container>

    <AccountSettingsDialog
      v-model="accountDialogVisible"
      @profile-updated="onProfileUpdated"
    />

    <el-dialog
      v-model="projectSwitchVisible"
      title="切换项目"
      width="440px"
      append-to-body
      destroy-on-close
      class="dashboard-project-switch-dialog"
      aria-describedby="project-switch-desc"
      @opened="onProjectSwitchDialogOpened"
    >
      <p id="project-switch-desc" class="dashboard-project-switch__desc">
        以下为模拟数据，支持按项目名称或标识模糊筛选；选择后将更新顶栏当前项目（仅前端演示）。
      </p>
      <el-input
        ref="projectSwitchInputRef"
        v-model="projectSwitchQuery"
        clearable
        placeholder="输入关键词筛选项目…"
        :prefix-icon="Search"
        aria-label="搜索项目名称或标识"
      />
      <el-scrollbar max-height="320" class="dashboard-project-switch__scroll">
        <template v-if="filteredMockProjects.length">
          <ul class="dashboard-project-switch__list" role="listbox" aria-label="项目列表">
            <li v-for="p in filteredMockProjects" :key="p.id" role="none">
              <button
                type="button"
                class="dashboard-project-switch__item"
                :class="{ 'dashboard-project-switch__item--active': p.id === tenantId }"
                role="option"
                :aria-selected="p.id === tenantId"
                @click="selectMockProject(p)"
              >
                <span class="dashboard-project-switch__name">{{ p.name }}</span>
                <span class="dashboard-project-switch__slug">{{ p.slug }}</span>
              </button>
            </li>
          </ul>
        </template>
        <el-empty v-else description="无匹配项目" :image-size="72" />
      </el-scrollbar>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Search } from "@element-plus/icons-vue";
import {
  Calendar,
  CircleCheck,
  Connection,
  Cpu,
  DataLine,
  Document,
  Edit,
  EditPen,
  Expand,
  Fold,
  FolderOpened,
  Grid,
  Guide,
  House,
  Lock,
  OfficeBuilding,
  Operation,
  Setting,
  Share,
  User,
  WarningFilled
} from "@element-plus/icons-vue";
import { useDsmsLogout } from "../composables/useDsmsLogout";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import {
  computeFoSubmissionReminderCount,
  SUBMISSION_TASKS_PERSIST_EVENT
} from "../composables/useSubmissionTaskFoReminderCount";
import {
  ensurePortalTenantReady,
  usePortalTenantContext
} from "../composables/usePortalTenantContext.js";
import {
  fetchMyFoBindings,
  fetchPendingApprovalCount,
  fetchSubmissionTasks,
  PORTAL_DATA_REFRESH_EVENT
} from "../api/portalApi.js";
import { foWorkflowProgressKey } from "../data/submissionFoWorkflowMock.js";
import { effectivePlatformRole, menuVisibilityForRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";
import AccountSettingsDialog from "../components/AccountSettingsDialog.vue";
import PortalBrandLogo from "../components/PortalBrandLogo.vue";
import ThemeToggleControl from "../components/ThemeToggleControl.vue";
import { useDsmsTheme } from "../composables/useDsmsTheme";

const { isDark } = useDsmsTheme();

const menuBackgroundColor = computed(() => (isDark.value ? "#0c1222" : "#ffffff"));
const menuTextColor = computed(() => (isDark.value ? "#e8eef7" : "#0f172a"));
const menuActiveTextColor = computed(() => (isDark.value ? "#ffffff" : "#152238"));

const ASIDE_COLLAPSED_KEY = "dsms_portal_aside_collapsed";
/** 略长于菜单 width 过渡，盖住 EP collapse Transition（out-in）衔接，避免文案晚一拍才消失 */
const MENU_COLLAPSE_LABEL_MS = 480;

const router = useRouter();
const route = useRoute();

/** 与 `el-menu-item` / `el-sub-menu` 的 `index` 一致，用于高亮与 `@select` */
const activeMenu = computed(() => {
  if (route.name === "dashboard-user-management") return "user-management";
  if (route.name === "dashboard-project-management") return "project-management";
  if (route.name === "dashboard-submission-status") return "submission-status";
  if (route.name === "dashboard-field-lifecycle-meta") return "field-lifecycle-meta";
  if (route.name === "dashboard-field-catalog") return "field-catalog";
  if (
    route.name === "dashboard-rule-relevance-questionnaire" ||
    route.name === "dashboard-rule-relevance-standard-expression"
  ) {
    return "rule-relevance";
  }
  if (
    route.name === "dashboard-rule-taxonomy-levels" ||
    route.name === "dashboard-rule-taxonomy-nodes" ||
    route.name === "dashboard-rule-taxonomy-field-classification" ||
    route.name === "dashboard-rule-taxonomy-classification-config" ||
    route.name === "dashboard-rule-taxonomy-classification-results"
  ) {
    return "rule-taxonomy";
  }
  if (
    route.name === "dashboard-rule-classification-levels" ||
    route.name === "dashboard-rule-classification-bindings"
  ) {
    return "rule-classification";
  }
  if (route.name === "dashboard-rule-security") {
    return "rule-security";
  }
  if (route.name === "dashboard-submission-task-detail" || route.name === "dashboard-submission-task") {
    return "submission-task";
  }
  if (route.name === "dashboard-approval") {
    return "approval";
  }
  if (route.name === "dashboard-document-resource") {
    return "document-resource";
  }
  return "home";
});

const logout = useDsmsLogout();
const accountDialogVisible = ref(false);
const asideCollapsed = ref(false);
/** 折叠瞬间先隐藏一级文案，避免 EP 过渡与 el-menu--collapse 不同步导致「收完宽文字还停半拍」 */
const suppressMenuLabels = ref(false);
let suppressMenuLabelsTimer = null;

/** 折叠宽度需与下方 .el-menu--collapse 的 CSS 变量一致：icon + padding*2 */
const asideWidth = computed(() => (asideCollapsed.value ? "52px" : "240px"));

const toggleAside = () => {
  if (suppressMenuLabelsTimer != null) {
    clearTimeout(suppressMenuLabelsTimer);
    suppressMenuLabelsTimer = null;
  }
  const nextCollapsed = !asideCollapsed.value;
  if (nextCollapsed) {
    suppressMenuLabels.value = true;
  } else {
    suppressMenuLabels.value = false;
  }
  asideCollapsed.value = nextCollapsed;
  if (nextCollapsed) {
    suppressMenuLabelsTimer = window.setTimeout(() => {
      suppressMenuLabels.value = false;
      suppressMenuLabelsTimer = null;
    }, MENU_COLLAPSE_LABEL_MS);
  }
};

const { tenantId, spaceId, tenantName, tenants, switchTenant, refreshTenants, ready } =
  usePortalTenantContext();
const { user: me, ensureCurrentUser, setCurrentUser } = useCurrentUser();

ensureCurrentUser();
ensurePortalTenantReady();

const filteredMockProjects = computed(() =>
  tenants.value.filter((p) => fuzzyProjectMatch(projectSwitchQuery.value, p))
);

const onProjectSwitchDialogOpened = () => {
  nextTick(() => {
    projectSwitchInputRef.value?.focus?.();
  });
};

const openProjectSwitchDialog = () => {
  projectSwitchQuery.value = "";
  projectSwitchVisible.value = true;
  nextTick(() => {
    tenantDropdownRef.value?.handleClose?.();
  });
};

const selectMockProject = async (p) => {
  await switchTenant(p);
  projectSwitchVisible.value = false;
  ElMessage.success(`已切换至「${p.name}」`);
  refreshFoSubmissionReminder();
  refreshApprovalPendingCount();
};

const currentTenantLabel = computed(() => tenantName.value || "项目");

const tenantDropdownRef = ref(null);
const projectSwitchVisible = ref(false);
const projectSwitchQuery = ref("");
const projectSwitchInputRef = ref(null);

function fuzzyProjectMatch(query, project) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const hay = `${project.name} ${project.slug || ""}`.toLowerCase();
  if (hay.includes(q)) return true;
  let from = 0;
  for (const ch of q) {
    const idx = hay.indexOf(ch, from);
    if (idx === -1) return false;
    from = idx + 1;
  }
  return true;
}

const tenantMenuAriaLabel = computed(
  () => `项目菜单，当前 ${currentTenantLabel.value}，按回车或空格打开`
);

const menuVis = computed(() => menuVisibilityForRole(effectivePlatformRole(me.value)));

const isFunctionFoRole = computed(() => effectivePlatformRole(me.value) === PLATFORM_ROLE.FUNCTION_FO);

const isSecOrAdminRole = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

const foSubmissionReminderCount = ref(0);
const approvalPendingCount = ref(0);

async function refreshFoSubmissionReminder() {
  if (!isFunctionFoRole.value) {
    foSubmissionReminderCount.value = 0;
    return;
  }
  if (!ready.value || !tenantId.value) {
    foSubmissionReminderCount.value = computeFoSubmissionReminderCount(me.value);
    return;
  }
  try {
    const [binding, tasks] = await Promise.all([
      fetchMyFoBindings(tenantId.value, spaceId.value),
      fetchSubmissionTasks(tenantId.value, spaceId.value)
    ]);
    const bound = new Set(binding.function_keys || []);
    foSubmissionReminderCount.value = tasks.filter((t) => {
      if (t.status !== "dispatched") return false;
      if (!bound.has(t.functionId)) return false;
      if (t.foCancellationRequested) return false;
      const k = foWorkflowProgressKey(t);
      return k === "not_started" || k === "relevance_draft" || k === "lifecycle_draft";
    }).length;
  } catch {
    foSubmissionReminderCount.value = computeFoSubmissionReminderCount(me.value);
  }
}

async function refreshApprovalPendingCount() {
  if (!isSecOrAdminRole.value) {
    approvalPendingCount.value = 0;
    return;
  }
  if (!ready.value || !tenantId.value) {
    approvalPendingCount.value = 0;
    return;
  }
  try {
    approvalPendingCount.value = await fetchPendingApprovalCount(tenantId.value, spaceId.value);
  } catch {
    approvalPendingCount.value = 0;
  }
}

const canAccessProjectManagement = computed(
  () => effectivePlatformRole(me.value) === PLATFORM_ROLE.SYSTEM_ADMIN
);

onMounted(async () => {
  try {
    asideCollapsed.value = localStorage.getItem(ASIDE_COLLAPSED_KEY) === "1";
  } catch (_e) {
    asideCollapsed.value = false;
  }
  await Promise.all([ensureCurrentUser(), ensurePortalTenantReady()]);
  await refreshTenants();
  refreshFoSubmissionReminder();
  refreshApprovalPendingCount();
  window.addEventListener(SUBMISSION_TASKS_PERSIST_EVENT, refreshFoSubmissionReminder);
  window.addEventListener(PORTAL_DATA_REFRESH_EVENT, () => {
    refreshFoSubmissionReminder();
    refreshApprovalPendingCount();
  });
});

watch(asideCollapsed, (v) => {
  try {
    localStorage.setItem(ASIDE_COLLAPSED_KEY, v ? "1" : "0");
  } catch (_e) {
    /* ignore */
  }
});

watch(me, () => {
  refreshFoSubmissionReminder();
  refreshApprovalPendingCount();
});

watch(
  () => route.name,
  () => {
    refreshFoSubmissionReminder();
  }
);

onBeforeUnmount(() => {
  if (suppressMenuLabelsTimer != null) {
    clearTimeout(suppressMenuLabelsTimer);
    suppressMenuLabelsTimer = null;
  }
  window.removeEventListener(SUBMISSION_TASKS_PERSIST_EVENT, refreshFoSubmissionReminder);
});

const userDisplayName = computed(() => {
  if (!me.value) return "加载中…";
  return me.value.full_name || me.value.username;
});

const userAvatarText = computed(() => {
  const name = me.value?.full_name || me.value?.username || "";
  return name ? name.slice(0, 1).toUpperCase() : "U";
});

const userAriaLabel = computed(() => `当前用户 ${userDisplayName.value}，点击展开账号菜单`);

const onTenantCommand = (command) => {
  if (command === "switch") {
    openProjectSwitchDialog();
  } else if (command === "manage") {
    if (!canAccessProjectManagement.value) {
      ElMessage.warning("仅系统管理员可打开项目管理。");
      return;
    }
    nextTick(() => {
      tenantDropdownRef.value?.handleClose?.();
    });
    router.push({ name: "dashboard-project-management" });
  }
};

const onUserCommand = (command) => {
  if (command === "account") {
    accountDialogVisible.value = true;
  } else if (command === "logout") {
    logout();
  }
};

const onProfileUpdated = (data) => {
  setCurrentUser(data);
};

const onMenuSelect = (index) => {
  if (index === "home") {
    router.push({ name: "dashboard-home" });
    return;
  }
  if (index === "user-management") {
    router.push({ name: "dashboard-user-management" });
    return;
  }
  if (index === "project-management") {
    router.push({ name: "dashboard-project-management" });
    return;
  }
  if (index === "submission-status") {
    router.push({ name: "dashboard-submission-status" });
    return;
  }
  if (index === "field-lifecycle-meta") {
    router.push({ name: "dashboard-field-lifecycle-meta" });
    return;
  }
  if (index === "field-catalog") {
    router.push({ name: "dashboard-field-catalog" });
    return;
  }
  if (index === "rule-relevance") {
    router.push({ name: "dashboard-rule-relevance-questionnaire" });
    return;
  }
  if (index === "rule-taxonomy") {
    router.push({ name: "dashboard-rule-taxonomy-levels" });
    return;
  }
  if (index === "rule-classification") {
    router.push({ name: "dashboard-rule-classification-levels" });
    return;
  }
  if (index === "rule-security") {
    router.push({ name: "dashboard-rule-security" });
    return;
  }
  if (index === "submission-task") {
    router.push({ name: "dashboard-submission-task" });
    return;
  }
  if (index === "approval") {
    router.push({ name: "dashboard-approval" });
    return;
  }
  if (index === "document-resource") {
    router.push({ name: "dashboard-document-resource" });
    return;
  }
  ElMessage.info("功能待接入");
};
</script>

<style scoped>
.dashboard-body {
  flex: 1;
  min-height: 0;
  width: 100%;
  min-width: 0;
  flex-direction: row;
}

@media (prefers-reduced-motion: no-preference) {
  .dsms-dashboard-page > header.dsms-portal-topbar {
    animation: dsms-shell-topbar-in var(--dsms-duration-medium) var(--dsms-ease-out-expo) both;
  }

  .dashboard-aside {
    animation: dsms-aside-shell-in var(--dsms-duration-medium) var(--dsms-ease-out-expo) 0.05s both;
    transition:
      width var(--dsms-duration-medium) var(--dsms-ease-out-expo),
      border-color var(--dsms-duration-short) var(--dsms-ease-standard);
  }

  .dashboard-main {
    animation: dsms-main-shell-in var(--dsms-duration-medium) var(--dsms-ease-out-expo) 0.09s both;
  }
}

.dashboard-aside {
  display: flex;
  flex-direction: column;
  /* 实底 + 不用 backdrop-filter：与 el-menu 折叠同时改宽度时，毛玻璃会每帧重绘导致明显卡顿 */
  background: var(--dsms-aside-surface);
  border-right: 1px solid var(--workspace-border);
  padding: 0;
  overflow: hidden;
  box-sizing: border-box;
}

@media (prefers-reduced-motion: reduce) {
  .dashboard-aside {
    transition: none;
  }
}

.aside-toolbar {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  height: 44px;
  padding: 0 8px;
  border-bottom: 1px solid var(--workspace-border);
  background: var(--dsms-aside-surface);
  box-sizing: border-box;
  transition: padding var(--dsms-duration-short) var(--dsms-ease-standard);
}

.aside-toolbar--collapsed {
  justify-content: center;
  padding: 0;
}

.aside-collapse-btn {
  color: var(--dsms-text-secondary);
  transition:
    color var(--dsms-duration-short) var(--dsms-ease-standard),
    transform var(--dsms-duration-instant) var(--dsms-ease-out-expo);
}

.aside-collapse-btn:hover {
  color: var(--dsms-text);
}

@media (prefers-reduced-motion: no-preference) {
  .aside-collapse-btn:active {
    transform: scale(0.94);
  }
}

.aside-nav {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  transform: translateZ(0);
}

.dashboard-menu {
  border-right: 0;
  background: transparent;
  /* 与 EP 折叠/展开、侧栏 width 过渡对齐；MENU_COLLAPSE_LABEL_MS 需略长于该时长 */
  --el-transition-duration: var(--dsms-duration-medium);
}

/* 默认折叠宽约 64px；收窄侧栏时同步收紧菜单变量，避免 aside 与菜单宽度不一致 */
.dashboard-menu.el-menu--collapse {
  --el-menu-icon-width: 22px;
  --el-menu-base-level-padding: 15px;
}

/* 折叠开始即隐藏一级文案（展开时不加该类，避免展开阶段文字被误藏） */
.dashboard-menu.dashboard-menu--suppress-labels :deep(> .el-menu-item > span),
.dashboard-menu.dashboard-menu--suppress-labels :deep(> .el-sub-menu > .el-sub-menu__title > span) {
  opacity: 0 !important;
  visibility: hidden !important;
  max-width: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  transition: none !important;
}

@media (prefers-reduced-motion: reduce) {
  .dashboard-menu {
    --el-transition-duration: 0.001ms;
  }
}

.dashboard-menu:not(.el-menu--collapse) {
  width: 100%;
}

/* 当前路由对应菜单项：浅底高亮；切换路由时不 remount 菜单，避免子菜单重播展开动画 */
.dashboard-menu :deep(.el-menu-item.is-active) {
  background-color: var(--el-color-primary-light-9);
  border-radius: 6px;
}

html.dark .dashboard-menu :deep(.el-menu-item.is-active) {
  background-color: rgba(255, 255, 255, 0.1);
}

.dashboard-main {
  padding: 28px;
  background: transparent;
  min-height: 0;
  overflow: auto;
}

.tenant-name {
  display: inline-block;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.tenant-caret {
  margin-left: 4px;
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.35);
  border: 1px solid var(--dsms-glass-border-subtle);
  border-radius: 10px;
  color: var(--dsms-text);
  cursor: pointer;
  font: inherit;
  outline: none;
  transition:
    background-color var(--dsms-duration-short) var(--dsms-ease-standard),
    border-color var(--dsms-duration-short) var(--dsms-ease-standard),
    box-shadow var(--dsms-duration-short) var(--dsms-ease-standard),
    transform var(--dsms-duration-instant) var(--dsms-ease-out-expo);
}

.user-trigger:hover {
  background: rgba(255, 255, 255, 0.65);
  border-color: var(--workspace-border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

@media (prefers-reduced-motion: no-preference) {
  .user-trigger:active {
    transform: scale(0.98);
  }
}

.user-trigger:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}

.user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #ffffff;
  font-size: 0.8125rem;
  font-weight: 600;
  flex-shrink: 0;
}

html.dark .user-avatar {
  background: #334155;
  color: #f8fafc;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-caret {
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
}

.dashboard-project-switch__desc {
  margin: 0 0 12px;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--dsms-text-secondary);
}

.dashboard-project-switch__scroll {
  margin-top: 12px;
  border: 1px solid var(--workspace-border);
  border-radius: 8px;
  background: var(--workspace-surface-2);
}

.dashboard-project-switch__list {
  list-style: none;
  margin: 0;
  padding: 8px;
}

.dashboard-project-switch__item {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 12px;
  margin: 0 0 6px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: var(--dsms-text);
  box-sizing: border-box;
  outline: none;
}

.dashboard-project-switch__item:last-child {
  margin-bottom: 0;
}

.dashboard-project-switch__item:hover {
  background: var(--workspace-surface);
}

.dashboard-project-switch__item:focus-visible {
  outline: 2px solid var(--dsms-focus-ring, var(--el-color-primary));
  outline-offset: 1px;
}

.dashboard-project-switch__item--active {
  border-color: var(--el-color-primary);
  background: var(--workspace-surface);
}

.dashboard-project-switch__name {
  font-weight: 600;
  font-size: 0.875rem;
}

.dashboard-project-switch__slug {
  font-size: 0.75rem;
  color: var(--dsms-text-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.dashboard-menu-item--with-badge {
  position: relative;
}

.dashboard-menu-item__badge {
  position: absolute;
  left: 6px;
  top: 6px;
  transform: none;
  line-height: 1;
}

.dashboard-menu-item__badge :deep(.el-badge__content) {
  border: none;
}

.el-menu--collapse .dashboard-menu-item__badge {
  left: 2px;
  top: 2px;
}
</style>

<style>
/* el-dialog 挂载到 body，不受父组件 scoped 影响 */
.dashboard-project-switch-dialog .el-dialog__body {
  padding-top: 8px;
}
</style>
