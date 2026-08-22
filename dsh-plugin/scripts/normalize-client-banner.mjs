// 规范化 client bundle 的 ModuleLoader banner。
// tsdown 的 banner/footer 已生成 window.__ModuleLoader__.load({id, factory}) 包装；
// 本脚本做二次校验：确保首行是 load 调用、末行闭合，并回写 sourcemap 引用。
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const out = join(__dirname, "..", "client", "client.js");

if (!existsSync(out)) {
  console.error("[normalize-client-banner] client/client.js not found; run tsdown first");
  process.exit(1);
}

let code = readFileSync(out, "utf8");
const loadOpen = code.startsWith("window.__ModuleLoader__.load({");
const loadClose = code.trimEnd().includes("return module.exports; } });");

if (!loadOpen || !loadClose) {
  console.error("[normalize-client-banner] banner/footer missing ModuleLoader wrapper");
  process.exit(1);
}

// 保证 sourceMappingURL 指向同目录 map（若 tsdown 已生成则不重复追加）
if (!/sourceMappingURL=client\.js\.map/.test(code)) {
  code = code.trimEnd() + "\n\n//# sourceMappingURL=client.js.map\n";
  writeFileSync(out, code, "utf8");
}

console.log("[normalize-client-banner] OK - client.js ModuleLoader wrapper verified");
