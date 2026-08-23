/** 解析 scripts 目录（下载/配套数据工具）。
 *  显式 override 或环境变量直接返回（路径存在性由调用方决定，作为 cwd 透传）；
 *  否则回退插件包根 assets/scripts（随包走，开箱即用）。 */
export declare function resolveScriptsDir(override?: string): string;
/** 解析 experiment 目录（SARscape 五步 batch + guard） */
export declare function resolveExperimentDir(override?: string): string;
/** 是否插件内置目录存在脚本（供工具在缺省时兜底报错提示） */
export declare function hasBundledScripts(): boolean;
/** 解析插件 assets 根（skill 的 resourceBase：SKILL.md 与 scripts/ experiment/ 并列于此）。 */
export declare function resolveAssetsDir(): string;
