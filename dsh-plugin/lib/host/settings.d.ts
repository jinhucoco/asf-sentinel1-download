import { Context } from "@deepseek-ai/cordis";
import z from "@deepseek-ai/schemastery";
/** 设置命名空间：须用 settingsNamespace() 工厂创建（Branded 类型）；
 *  dsh-settings 校验 /^[a-z][a-z0-9-]*$/，必须是小写 kebab-case（"insarGenie" 会抛 TypeError） */
export declare const SETTINGS_NS: import("@deepseek-ai/dsh-settings").SettingsNamespace;
/** 设置项 schema（enviIdl/sarscapeLib 的默认值是兜底；实际值由 probeDefaults 在 base 层覆盖） */
export declare const SettingsSchema: z<Schemastery.ObjectS<{
    earthdataUser: z<string, string>;
    earthdataPassword: z<string, string>;
    gacosEmail: z<string, string>;
    /** GACOS 邮箱 IMAP 授权码 —— 含 IMAP 术语更具体（明确是哪个邮箱的 IMAP 授权码）；
     *  当前 gacos_fetch.py 只实现 IMAP 收取，故字段语义即 IMAP 授权码 */
    gacosImapAuthCode: z<string, string>;
    enviIdl: z<string, string>;
    sarscapeLib: z<string, string>;
    workDir: z<string, string>;
    /** 精密轨道目录：默认 <实验目录>/poeorb，可覆盖为公共轨道库（**不探测**，用户自选存储位置） */
    poeorbDir: z<string, string>;
}>, Schemastery.ObjectT<{
    earthdataUser: z<string, string>;
    earthdataPassword: z<string, string>;
    gacosEmail: z<string, string>;
    /** GACOS 邮箱 IMAP 授权码 —— 含 IMAP 术语更具体（明确是哪个邮箱的 IMAP 授权码）；
     *  当前 gacos_fetch.py 只实现 IMAP 收取，故字段语义即 IMAP 授权码 */
    gacosImapAuthCode: z<string, string>;
    enviIdl: z<string, string>;
    sarscapeLib: z<string, string>;
    workDir: z<string, string>;
    /** 精密轨道目录：默认 <实验目录>/poeorb，可覆盖为公共轨道库（**不探测**，用户自选存储位置） */
    poeorbDir: z<string, string>;
}>>;
export type Settings = ReturnType<typeof SettingsSchema>;
/**
 * 注册设置命名空间。
 * 注意：installSettingsSection 签名是 5 参数
 *   installSettingsSection<T>(ctx, ns, schema, entry, hooks)
 * 其中 ns 必须是 settingsNamespace() 的返回值；entry 是默认值实例（composition 层 base 值）；
 * hooks 提供 setSource/onChange（可空实现）。
 *
 * 启动时路径探测：探测结果作为 entry（base 层）填入，用户设置的 user 层仍能覆盖，
 * 普通用户无需手动填 ENVI IDL / SARscape 路径。
 */
export declare function registerSettings(ctx: Context): void;
