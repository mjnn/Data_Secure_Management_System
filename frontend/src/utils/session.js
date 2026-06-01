import { clearCurrentUser } from "../composables/useCurrentUser.js";
import { resetPortalTenantContext } from "../composables/usePortalTenantContext.js";

export function clearLocalSession() {
  clearCurrentUser();
  resetPortalTenantContext();
  localStorage.removeItem("dsms_access_token");
  localStorage.removeItem("dsms_refresh_token");
}
