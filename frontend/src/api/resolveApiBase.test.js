import { describe, expect, it } from "vitest";
import { resolveApiBase } from "./resolveApiBase.js";

describe("resolveApiBase", () => {
  it("prefers explicit VITE_API_BASE", () => {
    expect(
      resolveApiBase({
        VITE_API_BASE: "https://api.example.com",
        DEV: true,
        BASE_URL: "/tools/dsms/"
      })
    ).toBe("https://api.example.com");
  });

  it("returns empty string in dev when VITE_API_BASE unset", () => {
    expect(
      resolveApiBase({
        VITE_API_BASE: "",
        DEV: true,
        BASE_URL: "/"
      })
    ).toBe("");
  });

  it("strips trailing slash from BASE_URL in production", () => {
    expect(
      resolveApiBase({
        DEV: false,
        BASE_URL: "/tools/dsms/"
      })
    ).toBe("/tools/dsms");
  });

  it("returns empty string when BASE_URL is root", () => {
    expect(
      resolveApiBase({
        DEV: false,
        BASE_URL: "/"
      })
    ).toBe("");
  });
});
