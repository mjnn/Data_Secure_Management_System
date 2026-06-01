import api from "../api.js";
import { appUrl } from "../utils/appBase.js";
import { clearLocalSession } from "../utils/session.js";

/** 清除令牌并回到登录页（与业务工作台一致） */
export function useDsmsLogout() {
  return async () => {
    const refreshToken = localStorage.getItem("dsms_refresh_token");
    if (refreshToken) {
      try {
        await api.post("/api/v1/auth/logout", { refresh_token: refreshToken });
      } catch {
        // 本地仍须清会话；网络失败不阻塞退出
      }
    }
    clearLocalSession();
    location.href = appUrl("login");
  };
}
