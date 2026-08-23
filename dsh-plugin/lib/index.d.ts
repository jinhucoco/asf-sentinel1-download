import { Context } from "@deepseek-ai/cordis";
export * from "./shared/types.js";
export { computeStatus } from "./host/status.js";
export { getTemplate, validateBaseline } from "./host/templates.js";
export declare const name = "insar-genie-dsh";
/** 声明本插件注入的服务：registerTools 用 ctx.tools，registerSettings 用 ctx.settings。
 *  缺省该数组时 Cordis 判定 `cannot get property "tools" without inject`，必须显式声明。 */
export declare const inject: string[];
/** 实验注册表存储目录（可通过设置覆盖） */
export declare const REGISTRY_DIR: () => string;
export declare function apply(ctx: Context): void;
