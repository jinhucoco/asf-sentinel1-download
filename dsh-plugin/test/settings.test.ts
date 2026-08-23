import { describe, it, expect } from "vitest";
import { SETTINGS_NS, SettingsSchema } from "../src/host/settings.js";

describe("settings namespace", () => {
  it("模块级加载不抛错，命名空间符合 dsh-settings 校验（小写 kebab-case）", () => {
    // 回归防线：若 settingsNamespace() 的 /^[a-z][a-z0-9-]*$/ 校验失败，
    // import 本模块本身就会抛 TypeError（如 "insarGenie" 含大写 G）。
    expect(SETTINGS_NS).toBe("insar-genie");
  });

  it("设置项 schema 可实例化（含默认值填充）", () => {
    const s = SettingsSchema({});
    expect(s.earthdataUser).toBe("");
    expect(s.poeorbDir).toBe("");
    expect(typeof s.sarscapeLib).toBe("string");
  });

  it("注册表目录为死字段，settings schema 不应暴露（registry 目录由 index.ts 硬编码 DSH_HOME/insar-genie）", () => {
    expect(SettingsSchema({})).not.toHaveProperty("registryDir");
  });
});
