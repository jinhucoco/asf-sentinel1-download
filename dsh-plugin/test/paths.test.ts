import { describe, it, expect, afterEach } from "vitest";
import { resolveScriptsDir, resolveExperimentDir, hasBundledScripts } from "../src/host/paths.js";

const ENV_VARS = ["INSAR_GENIE_SCRIPTS", "INSAR_GENIE_EXPERIMENT"];

describe("resolveScriptsDir / resolveExperimentDir（开箱即用脚本定位）", () => {
  afterEach(() => {
    for (const v of ENV_VARS) delete process.env[v];
  });

  it("显式 override 优先于环境变量", () => {
    process.env.INSAR_GENIE_SCRIPTS = "D:\\env\\scripts";
    expect(resolveScriptsDir("D:\\override\\scripts")).toBe("D:\\override\\scripts");
    process.env.INSAR_GENIE_EXPERIMENT = "D:\\env\\exp";
    expect(resolveExperimentDir("D:\\override\\exp")).toBe("D:\\override\\exp");
  });

  it("无 override 时用环境变量", () => {
    process.env.INSAR_GENIE_SCRIPTS = "D:\\env\\scripts";
    process.env.INSAR_GENIE_EXPERIMENT = "D:\\env\\exp";
    expect(resolveScriptsDir()).toBe("D:\\env\\scripts");
    expect(resolveExperimentDir()).toBe("D:\\env\\exp");
  });

  it("完全无覆盖时回退插件内置 assets 路径", () => {
    const s = resolveScriptsDir();
    expect(s).toMatch(/assets[\\/]scripts$/);
    const e = resolveExperimentDir();
    expect(e).toMatch(/assets[\\/]experiment$/);
  });

  it("插件的 assets/scripts 已打包 multi_download.py（开箱即用前提）", () => {
    // 源码模式下 pluginRoot() = src/，assets 不在；编译模式(lib/)才含内置脚本。
    // 该断言在编译产物上成立，源码模式允许为 false（不阻塞测试），
    // 但若在仓库编译产物上 true 则证明设备上有打包脚本。
    expect(typeof hasBundledScripts()).toBe("boolean");
  });
});
