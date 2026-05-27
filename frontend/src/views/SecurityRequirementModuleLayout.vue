<template>
  <div v-if="meReady && isSecOrAdmin" class="srm-layout">
    <router-view :key="route.fullPath" />
  </div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { effectivePlatformRole, PLATFORM_ROLE } from "../composables/usePortalMenuVisibility";

const route = useRoute();
const router = useRouter();
const { user: me, ready: meReady, ensureCurrentUser } = useCurrentUser();

ensureCurrentUser();

const isSecOrAdmin = computed(() => {
  const r = effectivePlatformRole(me.value);
  return r === PLATFORM_ROLE.SYSTEM_ADMIN || r === PLATFORM_ROLE.SECURITY_FO;
});

onMounted(async () => {
  await ensureCurrentUser();
  const role = effectivePlatformRole(me.value);
  if (role !== PLATFORM_ROLE.SYSTEM_ADMIN && role !== PLATFORM_ROLE.SECURITY_FO) {
    ElMessage.warning("仅数据安全 FO / 系统管理员可访问安全要求配置。");
    await router.replace({ name: "dashboard-home" });
  }
});
</script>

<style scoped>
.srm-layout {
  min-width: 0;
}
</style>
