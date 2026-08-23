import z from "@deepseek-ai/schemastery";
import { installSettingsSection, settingsNamespace } from "@deepseek-ai/dsh-settings";
/** 设置命名空间：须用 settingsNamespace() 工厂创建（Branded 类型）；
 *  dsh-settings 校验 /^[a-z][a-z0-9-]*$/，必须是小写 kebab-case（"insarGenie" 会抛 TypeError） */
export const SETTINGS_NS = settingsNamespace("insar-genie");
/** 设置项 schema */
export const SettingsSchema = z.object({
    earthdataUser: z.string().default(""),
    earthdataPassword: z.string().default(""),
    gacosEmail: z.string().default(""),
    /** GACOS 邮箱授权码 —— 命名用"邮箱授权码"而非"IMAP 授权码"（普通用户不懂 IMAP 术语；
     *  当前 gacos_fetch.py 只实现 IMAP 收取，改称邮箱授权码后未来扩展 POP3 也复用此字段） */
    gacosImapAuthCode: z.string().default(""),
    enviIdl: z.string().default("C:\\Program Files\\Harris\\ENVI56\\IDL88\\bin\\bin.x86_64\\envi_idl.exe"),
    sarscapeLib: z.string().default("C:\\Program Files\\SARMAP SA\\SARscape"),
    workDir: z.string().default("G:\\"),
    /** 精密轨道目录：默认 <实验目录>/poeorb，可覆盖为公共轨道库 */
    poeorbDir: z.string().default(""),
});
/**
 * 注册设置命名空间。
 * 注意：installSettingsSection 签名是 5 参数
 *   installSettingsSection<T>(ctx, ns, schema, entry, hooks)
 * 其中 ns 必须是 settingsNamespace() 的返回值；entry 是默认值实例；
 * hooks 提供 setSource/onChange（可空实现）。
 */
export function registerSettings(ctx) {
    // 注：schemastery 3.18.1 的 Schema 无 parse() 方法，直接调用 schema 即校验并填充默认值
    installSettingsSection(ctx, SETTINGS_NS, SettingsSchema, SettingsSchema({}), {
        setSource() { },
        onChange() { },
    });
}
