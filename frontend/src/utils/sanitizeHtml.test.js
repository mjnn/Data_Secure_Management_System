import { describe, expect, it } from "vitest";
import { sanitizeHtml } from "./sanitizeHtml.js";

describe("sanitizeHtml", () => {
  it("strips script tags and event handlers", () => {
    const dirty = '<p>ok</p><script>alert(1)</script><img src=x onerror="alert(1)">';
    const clean = sanitizeHtml(dirty);
    expect(clean).not.toContain("<script");
    expect(clean).not.toContain("onerror");
    expect(clean).toContain("<p>ok</p>");
  });

  it("returns empty string for falsy input", () => {
    expect(sanitizeHtml("")).toBe("");
    expect(sanitizeHtml(null)).toBe("");
  });
});
