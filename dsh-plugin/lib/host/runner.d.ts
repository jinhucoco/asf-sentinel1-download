export interface RunResult {
    exitCode: number | null;
    stdout: string;
    stderr: string;
}
/** 执行 python 脚本，捕获输出（复用 dsh-remote-web-ui update.ts 的 spawn 模式）。
 *  timeoutMs 缺省为 undefined = 不设超时（下载数小时级，禁止默认 10 分钟掐断）；
 *  传入正数才启用超时。 */
export declare function runPython(pythonBin: string, args: string[], cwd: string, timeoutMs?: number): Promise<RunResult>;
