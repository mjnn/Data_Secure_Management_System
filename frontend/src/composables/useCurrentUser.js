/** 全站当前登录用户（模块级单例，避免各路由重复请求 /api/v1/users/me） */

import { ref } from "vue";
import api from "../api";

const user = ref(null);
const loading = ref(false);
const ready = ref(false);
let inflight = null;

export function clearCurrentUser() {
  user.value = null;
  ready.value = false;
  loading.value = false;
  inflight = null;
}

export function setCurrentUser(data) {
  user.value = data ?? null;
  ready.value = true;
}

/**
 * @param {{ force?: boolean }} [opts]
 * @returns {Promise<object|null>}
 */
export async function fetchCurrentUser(opts = {}) {
  const { force = false } = opts;
  if (!force && ready.value) return user.value;
  if (!force && inflight) return inflight;

  const token =
    typeof localStorage !== "undefined" ? localStorage.getItem("dsms_access_token") : null;
  if (!token) {
    ready.value = true;
    user.value = null;
    return null;
  }

  loading.value = true;
  inflight = (async () => {
    try {
      const { data } = await api.get("/api/v1/users/me");
      user.value = data;
      return data;
    } catch {
      user.value = null;
      return null;
    } finally {
      ready.value = true;
      loading.value = false;
      inflight = null;
    }
  })();
  return inflight;
}

export function useCurrentUser() {
  return {
    user,
    me: user,
    loading,
    ready,
    ensureCurrentUser: fetchCurrentUser,
    refreshCurrentUser: () => fetchCurrentUser({ force: true }),
    setCurrentUser,
    clearCurrentUser
  };
}
