import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync, existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRegistry } from "../src/host/registry.js";

let dir: string;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "insar-reg-"));
});
afterEach(() => rmSync(dir, { recursive: true, force: true }));

describe("createRegistry", () => {
  it("创建空注册表（无文件时）", () => {
    const reg = createRegistry(dir);
    expect(reg.list()).toEqual([]);
  });
  it("创建实验并持久化", () => {
    const reg = createRegistry(dir);
    const id = reg.create({
      name: "minqin",
      terrain: "desert",
      dir: "G:/minqin1",
      dataDirs: { slc: "G:/slc", poeorb: "G:/poeorb", gacos: "G:/gacos", dem: "G:/dem" },
      params: { rgLooks: 8, azLooks: 2, maxTimeBaselineDays: 180, maxPercBaseline: 2,
        filtering: "GOLDSTEIN", goldsteinWinSize: 64, unwrap: "MCF", unwrapCohThreshold: 0.2,
        useGacos: true, demFile: "G:/dem/minqin" },
      status: "draft",
    });
    expect(reg.get(id)?.dataDirs.poeorb).toBe("G:/poeorb");
    // 持久化文件存在
    expect(existsSync(join(dir, "experiments.json"))).toBe(true);
    // 重新加载仍能读
    const reg2 = createRegistry(dir);
    expect(reg2.get(id)?.name).toBe("minqin");
  });
  it("更新状态", () => {
    const reg = createRegistry(dir);
    const id = reg.create({ name: "x", terrain: "urban", dir: "G:/x",
      dataDirs: { slc: "", poeorb: "", gacos: "", dem: "" },
      params: { rgLooks: 5, azLooks: 1, maxTimeBaselineDays: 180, maxPercBaseline: 2,
        filtering: "GOLDSTEIN", goldsteinWinSize: 64, unwrap: "MCF", unwrapCohThreshold: 0.3,
        useGacos: true, demFile: "" },
      status: "draft" });
    reg.update(id, { status: "running" });
    expect(reg.get(id)?.status).toBe("running");
  });
});
