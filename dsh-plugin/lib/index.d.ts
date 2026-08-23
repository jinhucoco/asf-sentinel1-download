import { Context } from "@deepseek-ai/cordis";
export * from "./shared/types.js";
export { computeStatus } from "./host/status.js";
export { getTemplate, validateBaseline } from "./host/templates.js";
export declare const name = "insar-genie-dsh";
/** 声明本插件注入的服务：registerTools 用 ctx.tools，registerSettings 用 ctx.settings，
 *  registerSkill 用 ctx.skills。缺省该数组时 Cordis 判定 `cannot get property without inject`。 */
export declare const inject: string[];
/** 实验注册表存储目录（可通过设置覆盖） */
export declare const REGISTRY_DIR: () => string;
/** 注册 insar-genie skill：插件自带的 AI 全流程工作流知识（assets/SKILL.md）。
 *  resourceBase 指向插件 assets 根 —— AI 加载 skill 后据此定位内置 scripts/ + experiment/。
 *  这让插件开箱即用：装插件 → 普通会话加载 insar-genie skill 即可全流程跑 SBAS，无需 agent preset。
 *  （单独导出以便测试 —— 不依赖 ctx.settings/tools 等其它服务。） */
export declare function registerSkill(ctx: Context): void;
export declare function apply(ctx: Context): void;
