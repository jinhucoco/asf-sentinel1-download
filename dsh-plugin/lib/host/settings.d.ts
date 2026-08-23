import { Context } from "@deepseek-ai/cordis";
import z from "@deepseek-ai/schemastery";
/** 设置命名空间：须用 settingsNamespace() 工厂创建（Branded 类型）；
 *  dsh-settings 校验 /^[a-z][a-z0-9-]*$/，必须是小写 kebab-case（"insarGenie" 会抛 TypeError） */
export declare const SETTINGS_NS: import("@deepseek-ai/dsh-settings").SettingsNamespace;
/** 设置项 schema */
export declare const SettingsSchema: z<Schemastery.ObjectS<{
    earthdataUser: z<string, string>;
    earthdataPassword: z<string, string>;
    gacosEmail: z<string, string>;
    gacosImapAuthCode: z<string, string>;
    enviIdl: z<string, string>;
    sarscapeLib: z<string, string>;
    workDir: z<string, string>;
    /** 精密轨道目录：默认 <实验目录>/poeorb，可覆盖为公共轨道库 */
    poeorbDir: z<string, string>;
    registryDir: z<string, string>;
}>, Schemastery.ObjectT<{
    earthdataUser: z<string, string>;
    earthdataPassword: z<string, string>;
    gacosEmail: z<string, string>;
    gacosImapAuthCode: z<string, string>;
    enviIdl: z<string, string>;
    sarscapeLib: z<string, string>;
    workDir: z<string, string>;
    /** 精密轨道目录：默认 <实验目录>/poeorb，可覆盖为公共轨道库 */
    poeorbDir: z<string, string>;
    registryDir: z<string, string>;
}>>;
export type Settings = ReturnType<typeof SettingsSchema>;
/**
 * 注册设置命名空间。
 * 注意：installSettingsSection 签名是 5 参数
 *   installSettingsSection<T>(ctx, ns, schema, entry, hooks)
 * 其中 ns 必须是 settingsNamespace() 的返回值；entry 是默认值实例；
 * hooks 提供 setSource/onChange（可空实现）。
 */
export declare function registerSettings(ctx: Context): void;
