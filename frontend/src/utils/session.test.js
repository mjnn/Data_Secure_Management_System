import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../composables/useCurrentUser.js", () => ({
  clearCurrentUser: vi.fn()
}));

vi.mock("../composables/usePortalTenantContext.js", () => ({
  resetPortalTenantContext: vi.fn()
}));

import { clearCurrentUser } from "../composables/useCurrentUser.js";
import { resetPortalTenantContext } from "../composables/usePortalTenantContext.js";
import { clearLocalSession } from "./session.js";

describe("clearLocalSession", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("clears tokens and user context", () => {
    localStorage.setItem("dsms_access_token", "a");
    localStorage.setItem("dsms_refresh_token", "r");

    clearLocalSession();

    expect(localStorage.getItem("dsms_access_token")).toBeNull();
    expect(localStorage.getItem("dsms_refresh_token")).toBeNull();
    expect(clearCurrentUser).toHaveBeenCalledOnce();
    expect(resetPortalTenantContext).toHaveBeenCalledOnce();
  });
});
