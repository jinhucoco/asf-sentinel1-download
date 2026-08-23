import { createRegistry } from "./registry.js";
/**
 * 注册三个工具到 host tools 注册表。
 * 依赖：ctx.tools（host 工具运行时）、registry。
 */
export declare function registerTools(ctx: any, deps: {
    registry: ReturnType<typeof createRegistry>;
}): void;
