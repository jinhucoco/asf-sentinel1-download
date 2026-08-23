import { Context } from "@deepseek-ai/cordis";
import z from "@deepseek-ai/schemastery";
import { installSettingsSection, settingsNamespace } from "@deepseek-ai/dsh-settings";
import { probeDefaults } from "./probe.js";

/** 设置命名空间：须用 settingsNamespace() 工厂创建（Branded 类型）；
 *  dsh-settings 校验 /^[a-z][a-z0-9-]*$/，必须是小写 kebab-case（"insarGenie" 会抛 TypeError） */
export const SETTINGS_NS = settingsNamespace("insar-genie");

/** 设置项 schema（enviIdl/sarscapeLib 的默认值是兜底；实际值由 probeDefaults 在 base 层覆盖） */
export const SettingsSchema = z.object({
  earthdataUser: z.string().default(""),
  earthdataPassword: z.string().default(""),
  gacosEmail: z.string().default(""),
  /** GACOS 邮箱 IMAP 授权码 —— 含 IMAP 术语更具体（明确是哪个邮箱的 IMAP 授权码）；
   *  当前 gacos_fetch.py 只实现 IMAP 收取，故字段语义即 IMAP 授权码 */
  gacosImapAuthCode: z.string().default(""),
  enviIdl: z.string().default(""),
  sarscapeLib: z.string().default(""),
  workDir: z.string().default("G:\\"),
  /** 精密轨道目录：默认 <实验目录>/poeorb，可覆盖为公共轨道库（**不探测**，用户自选存储位置） */
  poeorbDir: z.string().default(""),
});
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
export function registerSettings(ctx: Context) {
  const probed = probeDefaults({ enviIdl: "", sarscapeLib: "" });
  // 注：schemastery 3.18.1 的 Schema 无 parse() 方法，直接调用 schema 即校验并填充默认值。
  // entry 是 composition 层 base 值：探测到的软件路径作为 base，缺失字段由 schema 默认补全。
  installSettingsSection(ctx, SETTINGS_NS, SettingsSchema, SettingsSchema(probed), {
    setSource() {},
    onChange() {},
  });
}
