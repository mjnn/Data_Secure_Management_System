import { describe, expect, it } from "vitest";
import { appBasePath, appUrl } from "./appBase.js";

describe("appBasePath", () => {
  it("normalizes ECS subpath with trailing slash", () => {
    expect(appBasePath({ BASE_URL: "/tools/dsms/" })).toBe("/tools/dsms/");
    expect(appBasePath({ BASE_URL: "/tools/dsms" })).toBe("/tools/dsms/");
  });

  it("returns root slash for default base", () => {
    expect(appBasePath({ BASE_URL: "/" })).toBe("/");
  });
});

describe("appUrl", () => {
  it("builds login path at site root", () => {
    expect(appUrl("login", { BASE_URL: "/" })).toBe("/login");
  });

  it("builds login path under ECS prefix", () => {
    expect(appUrl("login", { BASE_URL: "/tools/dsms/" })).toBe("/tools/dsms/login");
  });

  it("strips leading slash from path argument", () => {
    expect(appUrl("/login", { BASE_URL: "/tools/dsms/" })).toBe("/tools/dsms/login");
  });
});
