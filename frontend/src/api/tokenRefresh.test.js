import { describe, expect, it, vi } from "vitest";
import { createRefreshCoordinator, handleUnauthorizedResponse } from "./tokenRefresh.js";

describe("createRefreshCoordinator", () => {
  it("deduplicates concurrent refresh calls", async () => {
    const coordinator = createRefreshCoordinator();
    let calls = 0;
    const refreshFn = vi.fn(async () => {
      calls += 1;
      await new Promise((r) => setTimeout(r, 20));
      return "token-a";
    });

    const [a, b] = await Promise.all([coordinator.run(refreshFn), coordinator.run(refreshFn)]);

    expect(a).toBe("token-a");
    expect(b).toBe("token-a");
    expect(refreshFn).toHaveBeenCalledTimes(1);
    expect(coordinator.pending).toBe(false);
  });
});

describe("handleUnauthorizedResponse", () => {
  it("retries once with new access token after 401", async () => {
    const coordinator = createRefreshCoordinator();
    const api = {
      request: vi.fn(async () => ({ data: { ok: true }, status: 200 }))
    };
    const onAuthFailure = vi.fn();
    const original = { headers: {}, url: "/x" };
    const error = { response: { status: 401 }, config: original };

    const result = await handleUnauthorizedResponse({
      error,
      api,
      coordinator,
      getRefreshToken: () => "refresh-1",
      refreshAccessToken: async () => "access-new",
      onAuthFailure
    });

    expect(result).toEqual({ data: { ok: true }, status: 200 });
    expect(original._retry).toBe(true);
    expect(original.headers.Authorization).toBe("Bearer access-new");
    expect(api.request).toHaveBeenCalledWith(original);
    expect(onAuthFailure).not.toHaveBeenCalled();
  });

  it("does not refresh again when request already retried", async () => {
    const coordinator = createRefreshCoordinator();
    const api = { request: vi.fn() };
    const onAuthFailure = vi.fn();
    const error = {
      response: { status: 401 },
      config: { _retry: true, headers: {} }
    };

    const result = await handleUnauthorizedResponse({
      error,
      api,
      coordinator,
      getRefreshToken: () => "refresh-1",
      refreshAccessToken: vi.fn(),
      onAuthFailure
    });

    expect(result).toBeNull();
    expect(api.request).not.toHaveBeenCalled();
    expect(onAuthFailure).not.toHaveBeenCalled();
  });

  it("calls onAuthFailure when refresh fails", async () => {
    const coordinator = createRefreshCoordinator();
    const api = { request: vi.fn() };
    const onAuthFailure = vi.fn();
    const error = { response: { status: 401 }, config: { headers: {} } };

    const result = await handleUnauthorizedResponse({
      error,
      api,
      coordinator,
      getRefreshToken: () => "refresh-1",
      refreshAccessToken: async () => {
        throw new Error("refresh failed");
      },
      onAuthFailure
    });

    expect(result).toBeNull();
    expect(onAuthFailure).toHaveBeenCalledOnce();
  });

  it("calls onAuthFailure when no refresh token", async () => {
    const coordinator = createRefreshCoordinator();
    const api = { request: vi.fn() };
    const onAuthFailure = vi.fn();
    const error = { response: { status: 401 }, config: { headers: {} } };

    const result = await handleUnauthorizedResponse({
      error,
      api,
      coordinator,
      getRefreshToken: () => null,
      refreshAccessToken: vi.fn(),
      onAuthFailure
    });

    expect(result).toBeNull();
    expect(onAuthFailure).toHaveBeenCalledOnce();
  });
});
