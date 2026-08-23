import { createRegistry } from "./registry.js";
/** settings 的值对象形状（与 SettingsSchema resolve 后的字段对齐，避免 schemastery 携带类型） */
export interface SettingsValue {
    earthdataUser: string;
    earthdataPassword: string;
    gacosEmail: string;
    gacosImapAuthCode: string;
    enviIdl: string;
    sarscapeLib: string;
    workDir: string;
    poeorbDir: string;
}
/**
 * 注册三个工具到 host tools 注册表。
 * 依赖：ctx.tools（host 工具运行时）、registry。
 */
export declare function registerTools(ctx: any, deps: {
    registry: ReturnType<typeof createRegistry>;
    settings?: {
        get(): SettingsValue | undefined;
    };
}): void;
