import { spawn } from "node:child_process";

export interface RunResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
}

const OUTPUT_CAP = 16 * 1024;

/** 执行 python 脚本，捕获输出（复用 dsh-remote-web-ui update.ts 的 spawn 模式）。
 *  timeoutMs 缺省为 undefined = 不设超时（下载数小时级，禁止默认 10 分钟掐断）；
 *  传入正数才启用超时。 */
export function runPython(
  pythonBin: string,
  args: string[],
  cwd: string,
  timeoutMs?: number,
): Promise<RunResult> {
  return new Promise((resolve) => {
    const child = spawn(pythonBin, args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    const capped = (s: string, chunk: Buffer) => {
      const next = s + chunk.toString("utf8");
      return next.length > OUTPUT_CAP ? next.slice(-OUTPUT_CAP) : next;
    };
    child.stdout?.on("data", (b: Buffer) => { stdout = capped(stdout, b); });
    child.stderr?.on("data", (b: Buffer) => { stderr = capped(stderr, b); });
    const timer = timeoutMs !== undefined && timeoutMs > 0
      ? setTimeout(() => {
          child.kill("SIGTERM");
          resolve({ exitCode: null, stdout, stderr: stderr + "\n[timeout]" });
        }, timeoutMs)
      : undefined;
    child.on("error", (err) => {
      if (timer) clearTimeout(timer);
      resolve({ exitCode: null, stdout, stderr: `${stderr}\n${String(err)}` });
    });
    child.on("close", (code) => {
      if (timer) clearTimeout(timer);
      resolve({ exitCode: code, stdout, stderr });
    });
  });
}
