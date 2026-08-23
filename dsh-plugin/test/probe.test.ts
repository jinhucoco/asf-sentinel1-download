import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { probeDefaults, probeEnviIdl, probeSarscape } from "../src/host/probe.js";

describe("probeEnviIdl / probeSarscape（启动时路径探测）", () => {
  let tmp: string;
  const savedEnv: Record<string, string | undefined> = {};
  const ENV_VARS = ["ENVI_IDL", "ENVI_IDL_DIR", "IDL_DIR", "SARSCAPE_HOME", "SARSCAPE_LIB"];

  beforeEach(() => {
    tmp = mkdtempSync(join(tmpdir(), "insar-probe-"));
    for (const v of ENV_VARS) {
      savedEnv[v] = process.env[v];
      delete process.env[v];
    }
  });

  afterEach(() => {
    for (const v of ENV_VARS) {
      if (savedEnv[v] !== undefined) process.env[v] = savedEnv[v];
      else delete process.env[v];
    }
    rmSync(tmp, { recursive: true, force: true });
  });

  it("注入根下找到 ENVI IDL（Harris/ENVIxx/IDLxx/bin/bin.x86_64/envi_idl.exe 两层深度）", () => {
    const fakeRoot = join(tmp, "Harris");
    const idlBin = join(fakeRoot, "ENVI56", "IDL88", "bin", "bin.x86_64");
    mkdirSync(idlBin, { recursive: true });
    writeFileSync(join(idlBin, "envi_idl.exe"), "x");
    const r = probeEnviIdl("/fallback", [fakeRoot]);
    expect(r).toBe(join(idlBin, "envi_idl.exe"));
  });

  it("注入根下找到 SARscape（SARMAP SA 子目录）", () => {
    const fakeRoot = join(tmp, "SARMAP SA");
    mkdirSync(join(fakeRoot, "SARscape"), { recursive: true });
    const r = probeSarscape("/fallback", [fakeRoot]);
    expect(r).toBe(join(fakeRoot, "SARscape"));
  });

  it("注入根找不到时返回 fallback（不抛错）", () => {
    expect(probeEnviIdl("/fb/env", [join(tmp, "none")])).toBe("/fb/env");
    expect(probeSarscape("/fb/sar", [join(tmp, "none")])).toBe("/fb/sar");
  });

  it("环境变量优先于注入根（用户自定义安装位置）", () => {
    const envPath = join(tmp, "custom_envi", "bin", "envi_idl.exe");
    mkdirSync(join(tmp, "custom_envi", "bin"), { recursive: true });
    writeFileSync(envPath, "x");
    process.env.ENVI_IDL = envPath;
    expect(probeEnviIdl("/fallback", [join(tmp, "none")])).toBe(envPath);
  });

  it("SARSCAPE 环境变量优先", () => {
    const sp = join(tmp, "my_sarscape");
    mkdirSync(sp, { recursive: true });
    process.env.SARSCAPE_HOME = sp;
    expect(probeSarscape("/fallback", [join(tmp, "none")])).toBe(sp);
  });

  it("probeDefaults 组合两个字段（环境变量）", () => {
    const enviPath = join(tmp, "envi.exe");
    writeFileSync(enviPath, "x");
    process.env.ENVI_IDL = enviPath;
    const sarPath = join(tmp, "sarsc");
    mkdirSync(sarPath, { recursive: true });
    process.env.SARSCAPE_HOME = sarPath;
    const r = probeDefaults({ enviIdl: "", sarscapeLib: "" });
    expect(r.enviIdl).toBe(enviPath);
    expect(r.sarscapeLib).toBe(sarPath);
  });
});
