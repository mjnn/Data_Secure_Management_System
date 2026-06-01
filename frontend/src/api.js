import axios from "axios";
import { resolveApiBase } from "./api/resolveApiBase.js";
import { appUrl } from "./utils/appBase.js";
import { clearLocalSession } from "./utils/session.js";
import { createRefreshCoordinator, handleUnauthorizedResponse } from "./api/tokenRefresh.js";

const baseURL = resolveApiBase(import.meta.env);

const api = axios.create({
  baseURL
});

const refreshCoordinator = createRefreshCoordinator();

function redirectToLogin() {
  clearLocalSession();
  if (!window.location.pathname.endsWith("/login") && !window.location.pathname.endsWith("login")) {
    location.href = appUrl("login");
  }
}

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("dsms_refresh_token");
  if (!refreshToken) {
    throw new Error("missing refresh token");
  }
  const { data } = await axios.post(`${baseURL || ""}/api/v1/auth/refresh`, {
    refresh_token: refreshToken
  });
  localStorage.setItem("dsms_access_token", data.access_token);
  localStorage.setItem("dsms_refresh_token", data.refresh_token);
  return data.access_token;
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("dsms_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const retried = await handleUnauthorizedResponse({
      error,
      api,
      coordinator: refreshCoordinator,
      getRefreshToken: () => localStorage.getItem("dsms_refresh_token"),
      refreshAccessToken,
      onAuthFailure: redirectToLogin
    });
    if (retried) {
      return retried;
    }
    return Promise.reject(error);
  }
);

export default api;
