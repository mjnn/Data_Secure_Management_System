<template>
  <div v-if="meReady && isSecOrAdmin" class="cgm-module">
    <ClassGradeModuleShell :active-page="activePage" />
    <div class="cgm-module__body">
      <router-view :key="route.fullPath" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import ClassGradeModuleShell from "../components/classification/ClassGradeModuleShell.vue";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const PAGE_BY_ROUTE_NAME = {
  "dashboard-rule-classification-levels": "levels",
  "dashboard-rule-classification-bindings": "bindings"
};

const route = useRoute();
const router = useRouter();
const { user: me, ready: meReady, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();

const isSecOrAdmin = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

/** @type {import('vue').ComputedRef<'levels' | 'bindings'>} */
const activePage = computed(() => {
  const fromMeta = route.meta?.classGradePage;
  if (fromMeta === "levels" || fromMeta === "bindings") return fromMeta;
  return PAGE_BY_ROUTE_NAME[route.name] || "levels";
});

onMounted(async () => {
  await ensureCurrentUser();
  const role = effectivePlatformRole(me.value);
  if (role !== PLATFORM_ROLE.SYSTEM_ADMIN && role !== PLATFORM_ROLE.SECURITY_FO) {
    ElMessage.warning("仅数据安全 FO / 系统管理员可访问密级绑定。");
    await router.replace({ name: "dashboard-home" });
  }
});
</script>

<style scoped>
.cgm-module {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.cgm-module__body {
  min-width: 0;
}
</style>
