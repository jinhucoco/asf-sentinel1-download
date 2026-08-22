import { describe, it, expect } from "vitest";
import { getTemplate, validateBaseline } from "../src/host/templates.js";

describe("getTemplate", () => {
  it("按地形返回参数模板", () => {
    const t = getTemplate("mining");
    expect(t.rgLooks).toBe(8);
    expect(t.maxPercBaseline).toBe(2);
  });
  it("未知地形抛错", () => {
    expect(() => getTemplate("ocean" as any)).toThrow("unknown terrain");
  });
});

describe("validateBaseline", () => {
  it("2% 通过", () => {
    expect(validateBaseline(2).ok).toBe(true);
  });
  it("4% 通过（扩大上限）", () => {
    expect(validateBaseline(4).ok).toBe(true);
  });
  it("45% 被拦截（防呆，杜绝事故）", () => {
    const r = validateBaseline(45);
    expect(r.ok).toBe(false);
    expect(r.message).toContain("2-4");
  });
  it("1% 被拦截（低于下限）", () => {
    expect(validateBaseline(1).ok).toBe(false);
  });
});
