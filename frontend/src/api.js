import axios from "axios";

// 开发环境走 Vite 代理（同域 /api → 后端），避免 localhost 与 127.0.0.1 混用导致 CORS 拦截登录
const baseURL = import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? "" : "http://127.0.0.1:8000");

const api = axios.create({
  baseURL
});

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
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem("dsms_refresh_token");
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${baseURL || ""}/api/v1/auth/refresh`, {
            refresh_token: refreshToken
          });
          localStorage.setItem("dsms_access_token", data.access_token);
          localStorage.setItem("dsms_refresh_token", data.refresh_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(error.config);
        } catch (_err) {
          localStorage.removeItem("dsms_access_token");
          localStorage.removeItem("dsms_refresh_token");
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
