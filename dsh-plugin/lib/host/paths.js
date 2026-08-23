import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
/**
 * 插件内置脚本路径定位（开箱即用核心）。
 *
 * 插件把完整 SBAS 执行链打包在 `assets/scripts`（下载/配套数据工具）和
 * `assets/experiment`（SARscape 五步 batch + guard）。本模块按插件安装根解析这些
 * 路径，使 `insar_run` / `insar_status` 等工具无需用户传 `scriptDir` 即可找到脚本。
 *
 * 解析链：
 * 1. 环境变量显式覆盖（INSAR_GENIE_SCRIPTS / INSAR_GENIE_EXPERIMENT）——用户自定义安装位置
 * 2. 插件包根下的 assets（默认，随包走）
 *
 * 注：宿主进程为 ESM（type:module），用 import.meta.url 定位本文件 → 上推到包根
 * （lib/host/paths.js 的 ../../ = 插件包根），assets 就在包根下。
 */
/** 当前模块所在目录（lib/host），上推两级到插件包根 */
function pluginRoot() {
    const here = dirname(fileURLToPath(import.meta.url));
    // here = <pkg>/lib/host → 上两级 = <pkg>
    return join(here, "..", "..");
}
/** 解析 scripts 目录（下载/配套数据工具）。
 *  显式 override 或环境变量直接返回（路径存在性由调用方决定，作为 cwd 透传）；
 *  否则回退插件包根 assets/scripts（随包走，开箱即用）。 */
export function resolveScriptsDir(override) {
    if (override)
        return override;
    if (process.env.INSAR_GENIE_SCRIPTS)
        return process.env.INSAR_GENIE_SCRIPTS;
    return join(pluginRoot(), "assets", "scripts");
}
/** 解析 experiment 目录（SARscape 五步 batch + guard） */
export function resolveExperimentDir(override) {
    if (override)
        return override;
    if (process.env.INSAR_GENIE_EXPERIMENT)
        return process.env.INSAR_GENIE_EXPERIMENT;
    return join(pluginRoot(), "assets", "experiment");
}
/** 是否插件内置目录存在脚本（供工具在缺省时兜底报错提示） */
export function hasBundledScripts() {
    return existsSync(join(pluginRoot(), "assets", "scripts", "multi_download.py"));
}
/** 解析插件 assets 根（skill 的 resourceBase：SKILL.md 与 scripts/ experiment/ 并列于此）。 */
export function resolveAssetsDir() {
    return join(pluginRoot(), "assets");
}
