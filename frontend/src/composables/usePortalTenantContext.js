import { ref } from "vue";
import { clearSpaceConfigCache } from "../stores/spaceConfigCache.js";
import { bootstrapSpaceConfig, fetchSpaces, fetchTenants } from "../api/dsmsSpaceApi.js";
import { bumpPortalDataListeners } from "../api/portalApi.js";

const TENANT_STORAGE_KEY = "dsms_portal_selected_tenant_v1";

/** @deprecated 旧版 mock 项目列表键，resolve 时清理 */
const LEGACY_PROJECTS_KEY = "dsms_portal_mock_projects_v1";
const LEGACY_CURRENT_TENANT_KEY = "dsms_portal_mock_current_tenant";

let legacyPortalStorageCleared = false;
let resolvePromise = null;

function clearLegacyPortalSessionStorage() {
  if (legacyPortalStorageCleared || typeof sessionStorage === "undefined") return;
  legacyPortalStorageCleared = true;
  try {
    sessionStorage.removeItem(LEGACY_PROJECTS_KEY);
    sessionStorage.removeItem(LEGACY_CURRENT_TENANT_KEY);
  } catch {
    /* ignore */
  }
}

/** 模块级共享状态（全站同一 tenant/space） */
const tenantId = ref(1);
const spaceId = ref(1);
const tenantName = ref("");
const spaceName = ref("");
const tenants = ref([]);
const loading = ref(false);
const ready = ref(false);

function readStoredTenantId() {
  try {
    const raw = localStorage.getItem(TENANT_STORAGE_KEY);
    if (raw) {
      const n = Number(JSON.parse(raw));
      if (Number.isFinite(n)) return n;
    }
  } catch {
    /* ignore */
  }
  return null;
}

function persistTenantId(id) {
  try {
    localStorage.setItem(TENANT_STORAGE_KEY, JSON.stringify(id));
  } catch {
    /* ignore */
  }
}

async function loadSpacesForTenant(tid) {
  const spaces = await fetchSpaces(tid);
  const space = spaces[0];
  if (space?.id) {
    spaceId.value = space.id;
    spaceName.value = space.name || space.space_key || "";
  }
}

async function resolvePortalTenant() {
  loading.value = true;
  clearLegacyPortalSessionStorage();
  try {
    tenants.value = await fetchTenants();
    const storedId = readStoredTenantId();
    const tenant = tenants.value.find((t) => t.id === storedId) || tenants.value[0];
    if (tenant?.id) {
      tenantId.value = tenant.id;
      tenantName.value = tenant.name || "";
      persistTenantId(tenant.id);
      await loadSpacesForTenant(tenant.id);
      await bootstrapSpaceConfig(tenantId.value, spaceId.value);
    }
    ready.value = true;
  } catch {
    ready.value = true;
  } finally {
    loading.value = false;
  }
}

/** 进入控制台后解析当前项目/空间（幂等，全站共享一次） */
export function ensurePortalTenantReady() {
  if (ready.value) return Promise.resolve();
  if (!resolvePromise) {
    resolvePromise = resolvePortalTenant().finally(() => {
      resolvePromise = null;
    });
  }
  return resolvePromise;
}

export function resetPortalTenantContext() {
  tenantId.value = 1;
  spaceId.value = 1;
  tenantName.value = "";
  spaceName.value = "";
  tenants.value = [];
  loading.value = false;
  ready.value = false;
  resolvePromise = null;
}

export function usePortalTenantContext() {
  async function switchTenant(nextTenant) {
    if (!nextTenant?.id) return;
    clearSpaceConfigCache();
    tenantId.value = nextTenant.id;
    tenantName.value = nextTenant.name || "";
    persistTenantId(nextTenant.id);
    await loadSpacesForTenant(nextTenant.id);
    await bootstrapSpaceConfig(tenantId.value, spaceId.value);
    ready.value = true;
    bumpPortalDataListeners();
  }

  async function refreshTenants() {
    tenants.value = await fetchTenants();
  }

  return {
    tenantId,
    spaceId,
    tenantName,
    spaceName,
    tenants,
    loading,
    ready,
    resolve: resolvePortalTenant,
    ensurePortalTenantReady,
    switchTenant,
    refreshTenants
  };
}

/** 非组件上下文读取当前 tenant/space id */
export function getPortalTenantIds() {
  return { tenantId: tenantId.value, spaceId: spaceId.value };
}
