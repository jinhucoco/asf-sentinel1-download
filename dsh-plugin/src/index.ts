import { Context } from "@deepseek-ai/cordis";
import { join } from "node:path";
import { createRegistry } from "./host/registry.js";
import { registerTools } from "./host/tools.js";
import { registerSettings } from "./host/settings.js";

export * from "./shared/types.js";
export { computeStatus } from "./host/status.js";
export { getTemplate, validateBaseline } from "./host/templates.js";

export const name = "insar-genie-dsh";

/** 声明本插件注入的服务：registerTools 用 ctx.tools，registerSettings 用 ctx.settings。
 *  缺省该数组时 Cordis 判定 `cannot get property "tools" without inject`，必须显式声明。 */
export const inject = ["tools", "settings"];

/** 实验注册表存储目录（可通过设置覆盖） */
export const REGISTRY_DIR = () =>
  process.env.DSH_HOME
    ? join(process.env.DSH_HOME, "insar-genie")
    : join(process.cwd(), ".insar-genie");

export function apply(ctx: Context) {
  const registry = createRegistry(REGISTRY_DIR());
  registerSettings(ctx);
  registerTools(ctx as never, { registry });
  // 注：cordis 4.0.1 的 Events 键不含 'dispose'，按简报意图保留空 disposer 占位，用 as any 适配
  ctx.on("dispose" as any, () => {});
}
