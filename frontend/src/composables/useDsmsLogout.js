import { clearCurrentUser } from "./useCurrentUser.js";
import { resetPortalTenantContext } from "./usePortalTenantContext.js";

/** 清除令牌并回到登录页（与业务工作台一致） */
export function useDsmsLogout() {
  return () => {
    clearCurrentUser();
    resetPortalTenantContext();
    localStorage.removeItem("dsms_access_token");
    localStorage.removeItem("dsms_refresh_token");
    location.href = "/login";
  };
}
