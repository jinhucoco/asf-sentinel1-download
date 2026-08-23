import { describe, it, expect, vi } from "vitest";
import { registerSkill } from "../src/index.js";

describe("insar-genie-dsh skill 注册（插件自包含 AI 工作流）", () => {
  function makeCtx() {
    const registered: Record<string, unknown>[] = [];
    return {
      ctx: {
        skills: {
          register: (skill: Record<string, unknown>) => {
            registered.push(skill);
            return () => {};
          },
        },
      } as any,
      registered,
    };
  }

  it("registerSkill 通过 ctx.skills.register 注册 insar-genie，resourceBase 指向插件 assets", () => {
    const { ctx, registered } = makeCtx();
    registerSkill(ctx);
    const skill = registered.find((s) => (s as { name?: string }).name === "insar-genie");
    expect(skill).toBeTruthy();
    expect((skill as { description?: string }).description).toMatch(/SBAS-InSAR 全链路/);
    const rb = (skill as { resourceBase?: { kind: string; path: string } }).resourceBase;
    expect(rb).toBeTruthy();
    expect(rb!.kind).toBe("directory");
    expect(rb!.path).toMatch(/assets$/);
  });

  it("skill 内容包含全流程关键章节（批处理 bat / 配套数据 / 守护监控）", () => {
    const { ctx, registered } = makeCtx();
    registerSkill(ctx);
    const skill = registered.find((s) => (s as { name?: string }).name === "insar-genie");
    const content = (skill as { content?: string }).content ?? "";
    expect(content).toMatch(/experiment\/bat/);
    expect(content).toMatch(/GACOS/);
    expect(content).toMatch(/sbas_guard/);
  });
});
