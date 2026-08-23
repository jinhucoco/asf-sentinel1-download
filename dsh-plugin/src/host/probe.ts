import { existsSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

/**
 * 启动时路径探测（普通用户友好）：
 * 自动定位 ENVI IDL 可执行文件与 SARscape 根目录，作为设置的 base 层默认值，
 * 用户无需（也无需被困扰于）手动填写专业软件路径。
 *
 * POEORB 目录**不探测**——它是用户可选的公共精密轨道库，路径随用户存储习惯变化，
 * 保持手动配置。工作目录同理（数据存放盘因人而异）。
 *
 * 探测顺序（ENVI）：注册表安装信息 → 常见安装位置（Program Files）→ 环境变量。
 * 全部失败时退回调用方传入的默认值。
 */

/** ENVI IDL 常见安装根（Program Files 下），按版本/厂商演进顺序探测 */
const ENVI_PF_ROOTS = [
  join("C:", "Program Files", "Harris"),
  join("C:", "Program Files", "Exelis"),
  join("C:", "Program Files (x86)", "Harris"),
  join("C:", "Program Files (x86)", "Exelis"),
];

/** SARscape 常见安装位置（Program Files 下） */
const SARSCAPE_PF_ROOTS = [
  join("C:", "Program Files", "SARMAP SA"),
  join("C:", "Program Files (x86)", "SARMAP SA"),
];

/** 环境变量候选（用户自定义安装位置时最有价值） */
const ENVI_IDL_ENV_VARS = ["ENVI_IDL", "ENVI_IDL_DIR", "IDL_DIR"];
const SARSCAPE_ENV_VARS = ["SARSCAPE_HOME", "SARSCAPE_LIB"];

/**
 * 在某目录下递归（限 4 层内）查找可执行文件名的第一个命中。
 * @param root 起始目录（不存在直接返回 undefined）
 * @param execName 目标可执行文件名，如 "envi_idl.exe"
 */
function findExecutable(root: string, execName: string): string | undefined {
  if (!existsSync(root)) return undefined;
  // 向下探测 4 层（ENVI 典型布局：Harris/ENVIxx/IDLxx/bin/bin.x86_64/envi_idl.exe 需 4 层）
  const depthLimit = 4;
  const queue: { dir: string; depth: number }[] = [{ dir: root, depth: 0 }];
  let guard = 0;
  while (queue.length > 0 && guard < 2000) {
    guard += 1;
    const { dir, depth } = queue.shift()!;
    let entries: string[];
    try {
      entries = readdirSync(dir);
    } catch {
      continue;
    }
    for (const entry of entries) {
      const abs = join(dir, entry);
      let isDir = false;
      try {
        // 无扩展名视为目录（envi_idl.exe 含 .，目录如 bin.x86_64 也含 . —— 需更可靠区分）
        const st = statSyncSafe(abs);
        isDir = st ? st.isDirectory() : false;
      } catch {
        continue;
      }
      if (isDir) {
        if (depth < depthLimit) queue.push({ dir: abs, depth: depth + 1 });
      } else if (entry.toLowerCase() === execName.toLowerCase()) {
        return abs;
      }
    }
  }
  return undefined;
}

/** 安全 stat：目录/文件类型；异常返回 undefined */
function statSyncSafe(p: string): { isDirectory(): boolean } | undefined {
  try {
    return statSync(p);
  } catch {
    return undefined;
  }
}

/** 探测 ENVI IDL 可执行文件路径 */
export function probeEnviIdl(fallback: string, roots: string[] = ENVI_PF_ROOTS): string {
  // 1) 环境变量
  for (const env of ENVI_IDL_ENV_VARS) {
    const v = process.env[env];
    if (v && existsSync(v)) return v;
  }
  // 2) 常见安装位置（Program Files）
  for (const root of roots) {
    const hit = findExecutable(root, "envi_idl.exe");
    if (hit) return hit;
  }
  return fallback;
}

/** 探测 SARscape 根目录 */
export function probeSarscape(fallback: string, roots: string[] = SARSCAPE_PF_ROOTS): string {
  // 1) 环境变量
  for (const env of SARSCAPE_ENV_VARS) {
    const v = process.env[env];
    if (v && existsSync(v)) return v;
  }
  // 2) 常见安装位置（Program Files）
  for (const root of roots) {
    if (existsSync(join(root, "SARscape"))) return join(root, "SARscape");
  }
  return fallback;
}

/** 启动时组合探测，返回 base 层默认值（给 SettingsSchema 注入） */
export function probeDefaults(
  current: { enviIdl: string; sarscapeLib: string },
): { enviIdl: string; sarscapeLib: string } {
  return {
    enviIdl: probeEnviIdl(current.enviIdl),
    sarscapeLib: probeSarscape(current.sarscapeLib),
  };
}
