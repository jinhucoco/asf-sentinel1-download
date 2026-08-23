import { defineConfig } from "tsdown";

/**
 * client 打包：把 src/client/index.ts 打包成 DSH ModuleLoader 格式的 client/client.js。
 * banner/footer 生成 `window.__ModuleLoader__.load({ id, factory: (require) => {...} })` 包装
 * （同 dshmarket 的 client.js 格式）。
 * 注意：entry 用 Record 格式（key=输出名，value=输入路径）；external 已废弃，用 deps.neverBundle。
 */
export default defineConfig({
  entry: { client: "src/client/index.ts" },
  outDir: "client",
  format: "cjs",
  platform: "browser",
  // cjs 默认输出 .cjs，但 DSH 期望 client.js —— 强制扩展名为 .js
  outExtensions: () => ({ js: ".js", dts: ".d.ts" }),
  deps: { neverBundle: [/^@deepseek-ai\//, /^react$/, /^react\/jsx-runtime$/] },
  banner: () =>
    `window.__ModuleLoader__.load({ id: "@dsh-custom/insar-genie-dsh", factory: (require) => {\n\n\t\tvar module = { exports: {} };\n\t\tvar exports = module.exports;`,
  footer: () => `return module.exports; } });`,
  minify: false,
  sourcemap: true,
  clean: true,
});
