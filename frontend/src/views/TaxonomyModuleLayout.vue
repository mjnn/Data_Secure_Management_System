<template>
  <div v-if="meReady && isSecOrAdmin" class="txs-module">
    <TaxonomyModuleShell :active-page="activePage" />
    <div class="txs-module__body">
      <router-view :key="route.fullPath" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import TaxonomyModuleShell from "../components/taxonomy/TaxonomyModuleShell.vue";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const TAXONOMY_PAGE_BY_ROUTE_NAME = {
  "dashboard-rule-taxonomy-levels": "levels",
  "dashboard-rule-taxonomy-nodes": "nodes",
  "dashboard-rule-taxonomy-field-classification": "fieldClassification",
  "dashboard-rule-taxonomy-classification-config": "classificationConfig",
  "dashboard-rule-taxonomy-classification-results": "classificationResults"
};

const route = useRoute();
const router = useRouter();
const { user: me, ready: meReady, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();

const isSecOrAdmin = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

/** @type {import('vue').ComputedRef<'levels' | 'nodes' | 'fieldClassification' | 'classificationConfig' | 'classificationResults'>} */
const activePage = computed(() => {
  const fromMeta = route.meta?.taxonomyPage;
  if (
    fromMeta === "levels" ||
    fromMeta === "nodes" ||
    fromMeta === "fieldClassification" ||
    fromMeta === "classificationConfig" ||
    fromMeta === "classificationResults"
  ) {
    return fromMeta;
  }
  const fromName = TAXONOMY_PAGE_BY_ROUTE_NAME[route.name];
  if (fromName) return fromName;
  return "levels";
});

onMounted(async () => {
  await ensureCurrentUser();
  const role = effectivePlatformRole(me.value);
  if (role !== PLATFORM_ROLE.SYSTEM_ADMIN && role !== PLATFORM_ROLE.SECURITY_FO) {
    ElMessage.warning("仅数据安全 FO / 系统管理员可访问数据分类标准配置。");
    await router.replace({ name: "dashboard-home" });
  }
});
</script>

<style scoped>
.txs-module {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.txs-module__body {
  min-width: 0;
}
</style>
