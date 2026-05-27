<template>
  <div v-if="meReady && isSecOrAdmin" class="rss-module">
    <RelevanceStandardModuleShell :active-page="activePage" />
    <div class="rss-module__body">
      <router-view :key="route.fullPath" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import RelevanceStandardModuleShell from "../components/relevance/RelevanceStandardModuleShell.vue";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const RELEVANCE_PAGE_BY_ROUTE_NAME = {
  "dashboard-rule-relevance-questionnaire": "questionnaire",
  "dashboard-rule-relevance-standard-expression": "expression"
};

const route = useRoute();
const router = useRouter();
const { user: me, ready: meReady, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();

const isSecOrAdmin = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

/** @type {import('vue').ComputedRef<'questionnaire' | 'expression'>} */
const activePage = computed(() => {
  const fromMeta = route.meta?.relevancePage;
  if (fromMeta === "questionnaire" || fromMeta === "expression") {
    return fromMeta;
  }
  const fromName = RELEVANCE_PAGE_BY_ROUTE_NAME[route.name];
  if (fromName) return fromName;
  return "questionnaire";
});

onMounted(async () => {
  await ensureCurrentUser();
  const role = effectivePlatformRole(me.value);
  if (role !== PLATFORM_ROLE.SYSTEM_ADMIN && role !== PLATFORM_ROLE.SECURITY_FO) {
    ElMessage.warning("仅数据安全 FO / 系统管理员可访问功能数据安全相关性配置。");
    await router.replace({ name: "dashboard-home" });
  }
});
</script>

<style scoped>
.rss-module {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.rss-module__body {
  min-width: 0;
}
</style>
