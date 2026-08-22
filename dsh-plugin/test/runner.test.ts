import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runPython } from "../src/host/runner.js";

let dir: string;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "insar-run-"));
});
afterEach(() => rmSync(dir, { recursive: true, force: true }));

describe("runPython", () => {
  it("执行成功脚本返回 exit 0 与输出", async () => {
    const script = join(dir, "ok.py");
    writeFileSync(script, "print('hello from script')");
    const r = await runPython(process.execPath, ["-e", "console.log('hi')"], dir);
    expect(r.exitCode).toBe(0);
    expect(r.stdout).toContain("hi");
  });
  it("失败脚本返回非 0 exitCode", async () => {
    const r = await runPython(process.execPath, ["-e", "process.exit(3)"], dir);
    expect(r.exitCode).toBe(3);
  });
});
