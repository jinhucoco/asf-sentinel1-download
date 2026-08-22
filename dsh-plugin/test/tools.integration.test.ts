import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// mock runPython：绝不真正调用 multi_download.py（下载是数小时级真实网络操作）
const { runPythonMock } = vi.hoisted(() => ({ runPythonMock: vi.fn() }));
vi.mock("../src/host/runner.js", () => ({ runPython: runPythonMock }));

import { registerTools } from "../src/host/tools.js";
import { createRegistry } from "../src/host/registry.js";

interface Tool {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  execute(args: Record<string, unknown>): Promise<unknown>;
}

function registerIntoFakeCtx(dir: string): Tool {
  const registry = createRegistry(join(dir, "registry"));
  const registered: Tool[] = [];
  const ctx: any = { tools: { register: (t: Tool) => registered.push(t) } };
  registerTools(ctx, { registry });
  const insarRun = registered.find((t) => t.name === "insar_run");
  if (!insarRun) throw new Error("insar_run not registered");
  return insarRun;
}

describe("insar_run → multi_download.py 真实 CLI 参数构造", () => {
  let dir: string;
  let insarRun: Tool;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "insar-tools-"));
    runPythonMock.mockReset();
    runPythonMock.mockResolvedValue({ exitCode: 0, stdout: "downloaded", stderr: "" });
    insarRun = registerIntoFakeCtx(dir);
  });

  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it("搜索路径：--aoi/--start/--end/--pol/--out 完整映射，cwd=scriptDir", async () => {
    const out = await insarRun.execute({
      scriptDir: "D:\\skill\\scripts",
      aoi: "C:\\aoi\\minqin.shp",
      start: "20240101",
      end: "20240630",
      pol: "VV+VH,VV",
      out: "G:\\s1",
    });
    expect(runPythonMock).toHaveBeenCalledTimes(1);
    expect(runPythonMock).toHaveBeenCalledWith(
      "python",
      [
        "multi_download.py",
        "--aoi", "C:\\aoi\\minqin.shp",
        "--start", "20240101",
        "--end", "20240630",
        "--pol", "VV+VH,VV",
        "--out", "G:\\s1",
      ],
      "D:\\skill\\scripts",
    );
    expect(out).toMatchObject({ ok: true });
  });

  it("清单路径：--list 映射（优先于搜索路径），cwd=scriptDir", async () => {
    await insarRun.execute({
      scriptDir: "D:\\skill\\scripts",
      list: "C:\\manifest.csv",
      pol: "VV",
      out: "G:\\s1",
    });
    expect(runPythonMock).toHaveBeenCalledWith(
      "python",
      ["multi_download.py", "--list", "C:\\manifest.csv", "--pol", "VV", "--out", "G:\\s1"],
      "D:\\skill\\scripts",
    );
  });

  it("未提供 list 且缺少 aoi/start/end 时抛错，不调用 runner", async () => {
    await expect(insarRun.execute({ scriptDir: "D:\\skill\\scripts" })).rejects.toThrow(/list|aoi/);
    expect(runPythonMock).not.toHaveBeenCalled();
  });

  it("exitCode !== 0 时抛 insar_run failed", async () => {
    runPythonMock.mockResolvedValue({ exitCode: 2, stdout: "", stderr: "usage error" });
    await expect(insarRun.execute({
      scriptDir: "D:\\skill\\scripts",
      aoi: "a.shp",
      start: "20240101",
      end: "20240201",
    })).rejects.toThrow(/insar_run failed/);
  });
});
