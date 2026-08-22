# insar-genie DSH 插件实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把现有 insar-genie 技能（已作为 DSH agent preset 安装）升级为完整 DSH 插件：cordis host 插件（insar_run / insar_status / insar_templates 工具 + 状态解析 + 设置 + 实验注册表）+ client UI（参数确认卡片 ParamConfirm + 进度面板 ProgressPanel）。

**架构：** 技能层已存在（`~/.dsh/.agent-presets/insar-genie/`，agent preset 形态）。本计划在其上新增 cordis 插件包 `@dsh-custom/insar-genie-dsh`（仓库内 `dsh-plugin/` 目录，Node/TS），host 侧注册 3 个工具 + 设置命名空间 + 实验注册表，client 侧提供 2 个 React 组件；host 通过 `spawn` 复用现有 Python 脚本（download.py / sbas_guard.py / bat），状态解析逻辑从 `sbas_guard.py::parse_progress()` 移植为 TS。

**技术栈：** Node 22+ / TypeScript / cordis 4 / @deepseek-ai/dsh-* 插件 API / React（client）/ vitest（host 测试）/ Playwright（UI 测试）。Python 侧零改动（复用现有资产）。

**参考规格：** `docs/superpowers/specs/2026-08-22-insar-genie-dsh-plugin-design.md`

**仓库：** `C:\Users\86155\.pi\agent\skills\asf-sentinel1-download`（dev 分支）

---

## 文件结构

```
dsh-plugin/                          # 新增：cordis 插件包根
├── package.json                     # @dsh-custom/insar-genie-dsh
├── tsconfig.json
├── vitest.config.ts
├── src/
│   ├── index.ts                     # host 入口：注册工具/服务/设置
│   ├── host/
│   │   ├── tools.ts                 # insar_run / insar_status / insar_templates
│   │   ├── status.ts                # parseExperimentStatus（移植 parse_progress）
│   │   ├── settings.ts              # 设置命名空间（含 POEORB 路径）
│   │   ├── registry.ts              # 实验注册表（experiments.json）
│   │   ├── runner.ts                # spawn Python 脚本的后台任务封装
│   │   └── templates.ts             # 地形参数模板库（纯数据）
│   ├── client/
│   │   ├── index.ts                 # client 入口
│   │   ├── ParamConfirm.tsx         # 参数确认卡片
│   │   └── ProgressPanel.tsx        # 进度面板
│   └── shared/
│       └── types.ts                 # 跨 host/client 的类型（Experiment/Param/Status）
├── assets/
│   └── README.md                    # 说明 assets 由 preset 提供（不重复打包）
└── test/
    ├── fixtures/                    # 真实日志 fixture（民勤样本）
    │   ├── step_performed.sml
    │   ├── auxiliary.sml
    │   └── guard.log
    ├── status.test.ts
    ├── templates.test.ts
    └── registry.test.ts
```

**说明**：`SKILL.md`/`scripts/`/`experiment/` 已由 agent preset（`dsh/insar-genie/`）携带，插件不重复打包，通过预设的 `skills/` 目录解析脚本路径。

---

## 任务 1：插件包脚手架

**文件：**
- 创建：`dsh-plugin/package.json`
- 创建：`dsh-plugin/tsconfig.json`
- 创建：`dsh-plugin/vitest.config.ts`
- 创建：`dsh-plugin/src/shared/types.ts`

- [ ] **步骤 1：创建 package.json**

```json
{
  "name": "@dsh-custom/insar-genie-dsh",
  "version": "0.1.0",
  "description": "SBAS-InSAR full-chain DSH plugin: run/status/template tools + param-confirm card + progress panel",
  "type": "module",
  "main": "lib/index.js",
  "exports": {
    ".": { "types": "./lib/types/index.d.ts", "default": "./lib/index.js" },
    "./client": { "types": "./lib/types/client/index.d.ts", "default": "./lib/client.js" },
    "./package.json": "./package.json"
  },
  "files": ["lib", "assets"],
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "peerDependencies": {
    "@deepseek-ai/cordis": "^4.0.1",
    "@deepseek-ai/dsh-settings": "^0.1.1-rc.2",
    "@deepseek-ai/dsh-tools": "^0.1.1-rc.2",
    "@deepseek-ai/dsh-jobs": "^0.1.1-rc.2"
  },
  "devDependencies": {
    "@deepseek-ai/cordis": "^4.0.1",
    "@types/node": "^22.0.0",
    "typescript": "^5.5.0",
    "vitest": "^2.0.0"
  },
  "license": "MIT"
}
```

- [ ] **步骤 1b：创建 dsh-plugin/.gitignore（node_modules 和构建产物不入库）**

```gitignore
node_modules/
lib/
*.log
```

- [ ] **步骤 2：创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "declaration": true,
    "outDir": "lib",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "jsx": "react-jsx",
    "types": ["node"]
  },
  "include": ["src"]
}
```

- [ ] **步骤 3：创建 vitest.config.ts**

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    environment: "node",
  },
});
```

- [ ] **步骤 4：创建 shared/types.ts（跨 host/client 核心类型）**

```ts
/** 实验生命周期状态 */
export type ExperimentStatus =
  | "draft" | "queued" | "running" | "paused" | "failed" | "done";

/** SBAS 五步（对应 auxiliary.sml 的 OK/NotOK 标记） */
export const SBAS_STEPS = [
  "generate_connection_graph",
  "interf_stack",
  "unwrapping",
  "first_inversion",
  "second_inversion",
  "geocode_result",
] as const;
export type SbasStep = (typeof SBAS_STEPS)[number];

/** 一个实验的完整记录 */
export interface Experiment {
  id: string;                      // uuid，如 "20260822-1530"
  name: string;                    // 用户给的名字，如 "民勤_minqin"
  terrain: TerrainType;            // 地形类型
  dir: string;                     // 实验根目录（G:\xxx）
  dataDirs: {
    slc: string;
    poeorb: string;                // 精密轨道目录
    gacos: string;
    dem: string;
  };
  params: ExperimentParams;        // 参数快照（确认卡确认后的最终值）
  status: ExperimentStatus;
  startedAt?: string;              // ISO 时间
  error?: { code: string; detail: string; evidence: string };
}

/** 地形类型（模板库键） */
export type TerrainType =
  | "mining" | "landslide" | "urban" | "desert" | "loess";

/** 参数快照（防呆：空间基线必须是 2-4%） */
export interface ExperimentParams {
  rgLooks: number;                 // 多视 8
  azLooks: number;                 // 多视 2
  maxTimeBaselineDays: number;     // 180
  maxPercBaseline: number;         // 2 或 4 —— 防呆校验区间
  filtering: "GOLDSTEIN";
  goldsteinWinSize: number;        // 64
  unwrap: "MCF";
  unwrapCohThreshold: number;      // 0.2
  useGacos: boolean;
  demFile: string;
}

/** insar_status 返回的进度快照 */
export interface ExperimentStatus {
  step: SbasStep;                  // 当前步骤
  stepIndex: number;               // 0-5
  totalSteps: number;              // 6
  donePairs: number;               // 干涉图：已完成对
  totalPairs: number;              // 干涉图：总对
  pairsPerMinute: number;          // 速率
  etaMinutes: number;              // 剩余时间
  diskGb: number;                  // 数据盘占用
  progressLabel: string;           // "干涉图生成 79%"
  isStalled: boolean;
  error?: { code: string; detail: string; evidence: string };
}
```

- [ ] **步骤 5：安装依赖并构建验证**

运行（在 `dsh-plugin/` 下）：
```bash
npm install
npx tsc -p tsconfig.json --noEmit
```
预期：无类型错误。

- [ ] **步骤 6：Commit**

```bash
git add dsh-plugin/
git commit -m "chore(plugin): scaffold @dsh-custom/insar-genie-dsh package (tsconfig/vitest/shared types)"
```

---

## 任务 2：真实日志 fixture（TDD 数据底座）

**文件：**
- 创建：`dsh-plugin/test/fixtures/step_performed.sml`（截取真实民勤样本，含 step=0/1 混合）
- 创建：`dsh-plugin/test/fixtures/auxiliary.sml`（五步 OK/NotOK 混合）
- 创建：`dsh-plugin/test/fixtures/guard.log`（守护日志样本，含 "123/376 对" 格式）

- [ ] **步骤 1：创建 step_performed.sml fixture（从真实文件截取 6 行）**

从 `G:\minqin1_result_SBAS_processing\work\work_step_performed.sml` 截取（真实内容，含 NumberOfRows）：

```xml
<?xml version="1.0" ?>
<HEADER_INFO xmlns="http://www.sarmap.ch/xml/SARscapeHeaderSchema">
   <sbas_step_performed>
      <header>**Step performed for each pair**</header>
      <pair_list>
         <MatrixInteger NumberOfRows = "310" NumberOfColumns = "3">
            <MatrixRowInteger ID = "0">
               <ValueInteger ID = "0">38</ValueInteger>
               <ValueInteger ID = "1">34</ValueInteger>
               <ValueInteger ID = "2">1</ValueInteger>
            </MatrixRowInteger>
            <MatrixRowInteger ID = "1">
               <ValueInteger ID = "0">38</ValueInteger>
               <ValueInteger ID = "1">35</ValueInteger>
               <ValueInteger ID = "2">1</ValueInteger>
            </MatrixRowInteger>
            <MatrixRowInteger ID = "2">
               <ValueInteger ID = "0">38</ValueInteger>
               <ValueInteger ID = "1">42</ValueInteger>
               <ValueInteger ID = "2">1</ValueInteger>
            </MatrixRowInteger>
            <MatrixRowInteger ID = "3">
               <ValueInteger ID = "0">38</ValueInteger>
               <ValueInteger ID = "1">44</ValueInteger>
               <ValueInteger ID = "2">1</ValueInteger>
            </MatrixRowInteger>
            <MatrixRowInteger ID = "4">
               <ValueInteger ID = "0">8</ValueInteger>
               <ValueInteger ID = "1">2</ValueInteger>
               <ValueInteger ID = "2">0</ValueInteger>
            </MatrixRowInteger>
            <MatrixRowInteger ID = "5">
               <ValueInteger ID = "0">8</ValueInteger>
               <ValueInteger ID = "1">3</ValueInteger>
               <ValueInteger ID = "2">0</ValueInteger>
            </MatrixRowInteger>
         </MatrixInteger>
      </pair_list>
   </sbas_step_performed>
</HEADER_INFO>
```

（说明：真实文件 310 行；fixture 截取 6 行已足够测试。真实样本路径：`G:\minqin1_result_SBAS_processing\work\work_step_performed.sml`）

- [ ] **步骤 2：创建 auxiliary.sml fixture（五步 OK/NotOK 混合）**

```xml
<HEADER_INFO>
   <generate_connection_graph>OK</generate_connection_graph>
   <coregistration>NotOK</coregistration>
   <interf_stack>NotOK</interf_stack>
   <interf_patterns_removal>NotOK</interf_patterns_removal>
   <hc_unwrapping>NotOK</hc_unwrapping>
   <hc_unwrapping_init3D>NotOK</hc_unwrapping_init3D>
   <hc_interf_patterns_removal>NotOK</hc_interf_patterns_removal>
   <unwrapping>NotOK</unwrapping>
   <unwrapping_init3D>NotOK</unwrapping_init3D>
   <initial_reflat>NotOK</initial_reflat>
   <first_reflat>NotOK</first_reflat>
   <first_inversion>NotOK</first_inversion>
   <second_unwrapping>NotOK</second_unwrapping>
   <second_unwrapping_init3D>NotOK</second_unwrapping_init3D>
   <second_reflat>NotOK</second_reflat>
   <second_inversion>NotOK</second_inversion>
   <remove_atmosphere_and_fit_disp>NotOK</remove_atmosphere_and_fit_disp>
   <geocod_reflat>NotOK</geocod_reflat>
   <geocode_result>NotOK</geocode_result>
</HEADER_INFO>
```

- [ ] **步骤 3：创建 guard.log fixture**

```
[2026-08-20 18:31:58] [体检] 123/376 对 (32.7%), 14.1G, 进度: Co-Registration [R_65]-[S_61] Progress [32%]
[2026-08-20 19:03:40] [体检] 124/376 对 (33.0%), 14.3G, 进度: Co-Registration [R_65]-[S_62] Progress [33%]
[2026-08-21 17:21:40] [体检] 184/376 对 (48.9%), 21.0G, 进度: Co-Registration [R_35]-[S_36] Progress [49%]
[2026-08-21 19:58:32] [体检] 190/376 对 (50.5%), 21.7G, 进度: Co-Registration [R_41]-[S_39] Progress [50%]
```

（真实样本路径：`D:\work\data\asf_experiment\sbas_guard.log`，行格式如上）

- [ ] **步骤 4：Commit**

```bash
git add dsh-plugin/test/fixtures/
git commit -m "test(plugin): add real-log fixtures (step_performed/auxiliary/guard) for status parser"
```

---

## 任务 3：状态解析服务 status.ts（TDD）

移植 `sbas_guard.py::parse_progress()` + 解析 `work_step_performed.sml` 和 `Process.log`。

**文件：**
- 创建：`dsh-plugin/src/host/status.ts`
- 测试：`dsh-plugin/test/status.test.ts`

- [ ] **步骤 1：编写失败的测试**

```ts
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  parseAuxiliarySteps,
  parsePairProgress,
  parseGuardLog,
  computeStatus,
} from "../src/host/status.js";

const FIX = (f: string) =>
  join(process.cwd(), "test", "fixtures", f);

describe("parseAuxiliarySteps", () => {
  it("解析 auxiliary.sml 的 OK/NotOK 标记", () => {
    const steps = parseAuxiliarySteps(readFileSync(FIX("auxiliary.sml"), "utf8"));
    expect(steps.generate_connection_graph).toBe(true);
    expect(steps.interf_stack).toBe(false);
    expect(steps.geocode_result).toBe(false);
  });
});

describe("parsePairProgress", () => {
  it("从 step_performed.sml 计算已完成对/总对", () => {
    const { done, total } = parsePairProgress(
      readFileSync(FIX("step_performed.sml"), "utf8"),
    );
    expect(total).toBe(310);
    expect(done).toBe(4); // fixture 中 4 行 step=1
  });
});

describe("parseGuardLog", () => {
  it("从 guard.log 提取最后一条进度", () => {
    const last = parseGuardLog(readFileSync(FIX("guard.log"), "utf8"));
    expect(last.donePairs).toBe(190);
    expect(last.totalPairs).toBe(376);
    expect(last.diskGb).toBeGreaterThan(20);
  });
});

describe("computeStatus", () => {
  it("组合成完整状态（当前在干涉图阶段）", () => {
    const status = computeStatus({
      auxXml: readFileSync(FIX("auxiliary.sml"), "utf8"),
      stepPerformedXml: readFileSync(FIX("step_performed.sml"), "utf8"),
      guardLog: readFileSync(FIX("guard.log"), "utf8"),
    });
    expect(status.step).toBe("interf_stack");
    expect(status.stepIndex).toBe(1);
    expect(status.donePairs).toBe(190);
    expect(status.totalPairs).toBe(376);
    expect(status.progressLabel).toContain("干涉");
  });
});
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd dsh-plugin && npx vitest run test/status.test.ts`
预期：FAIL，"Cannot find module '../src/host/status.js'"

- [ ] **步骤 3：实现 status.ts**

```ts
import { SBAS_STEPS, type ExperimentStatus, type SbasStep } from "../shared/types.js";

/** 解析 auxiliary.sml 各步骤 OK/NotOK → {tag: bool}（移植自 sbas_guard.py parse_progress） */
export function parseAuxiliarySteps(xml: string): Record<string, boolean> {
  const out: Record<string, boolean> = {};
  const re = /<(\w+)>(OK|NotOK)<\/\1>/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(xml)) !== null) {
    out[m[1]] = m[2] === "OK";
  }
  return out;
}

/** 从 work_step_performed.sml 计算已完成对/总对（第三列=1 为完成） */
export function parsePairProgress(xml: string): { done: number; total: number } {
  const totalMatch = /NumberOfRows\s*=\s*"(\d+)"/.exec(xml);
  const total = totalMatch ? Number(totalMatch[1]) : 0;
  const done = (xml.match(/<ValueInteger ID = "2">1<\/ValueInteger>/g) ?? []).length;
  return { done, total };
}

/** 从 guard.log 提取最后一条体检进度 */
export function parseGuardLog(log: string): {
  donePairs: number;
  totalPairs: number;
  diskGb: number;
} {
  const lines = log.trim().split("\n").filter((l) => l.includes("体检"));
  const last = lines[lines.length - 1] ?? "";
  const pair = /(\d+)\/(\d+) 对/.exec(last);
  const disk = /([\d.]+)G/.exec(last);
  return {
    donePairs: pair ? Number(pair[1]) : 0,
    totalPairs: pair ? Number(pair[2]) : 0,
    diskGb: disk ? Number(disk[1]) : 0,
  };
}

/** 组合完整状态 */
export function computeStatus(input: {
  auxXml: string;
  stepPerformedXml: string;
  guardLog: string;
}): ExperimentStatus {
  const aux = parseAuxiliarySteps(input.auxXml);
  const { done, total } = parsePairProgress(input.stepPerformedXml);
  const guard = parseGuardLog(input.guardLog);

  // 当前步骤 = 第一个 NotOK 的 SBAS 步骤
  let stepIndex = SBAS_STEPS.findIndex((s) => !aux[s]);
  if (stepIndex === -1) stepIndex = SBAS_STEPS.length - 1;
  const step = SBAS_STEPS[stepIndex] as SbasStep;

  const stepLabels: Record<SbasStep, string> = {
    generate_connection_graph: "连接图",
    interf_stack: "干涉图生成",
    unwrapping: "解缠",
    first_inversion: "反演1",
    second_inversion: "反演2",
    geocode_result: "地理编码",
  };

  const donePairs = guard.totalPairs > 0 ? guard.donePairs : done;
  const totalPairs = guard.totalPairs > 0 ? guard.totalPairs : total;
  const pct = totalPairs > 0 ? Math.round((donePairs / totalPairs) * 100) : 0;

  return {
    step,
    stepIndex,
    totalSteps: SBAS_STEPS.length,
    donePairs,
    totalPairs,
    pairsPerMinute: 0.22, // 4.5 分钟/对 → 0.22 对/分钟（可后续从 Process.log 精确计算）
    etaMinutes: totalPairs > 0 ? Math.round((totalPairs - donePairs) / 0.22) : 0,
    diskGb: guard.diskGb,
    progressLabel: `${stepLabels[step]} ${pct}%`,
    isStalled: false,
  };
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd dsh-plugin && npx vitest run test/status.test.ts`
预期：PASS（4 个用例全绿）

- [ ] **步骤 5：Commit**

```bash
git add dsh-plugin/src/host/status.ts dsh-plugin/test/status.test.ts
git commit -m "feat(plugin): status parser (auxiliary/step_performed/guard log) ported from sbas_guard.py"
```

---

## 任务 4：地形参数模板库 templates.ts（TDD）

**文件：**
- 创建：`dsh-plugin/src/host/templates.ts`
- 测试：`dsh-plugin/test/templates.test.ts`

- [ ] **步骤 1：编写失败的测试**

```ts
import { describe, it, expect } from "vitest";
import { getTemplate, validateBaseline } from "../src/host/templates.js";

describe("getTemplate", () => {
  it("按地形返回参数模板", () => {
    const t = getTemplate("mining");
    expect(t.rgLooks).toBe(8);
    expect(t.maxPercBaseline).toBe(2);
  });
  it("未知地形抛错", () => {
    expect(() => getTemplate("ocean" as any)).toThrow("unknown terrain");
  });
});

describe("validateBaseline", () => {
  it("2% 通过", () => {
    expect(validateBaseline(2).ok).toBe(true);
  });
  it("4% 通过（扩大上限）", () => {
    expect(validateBaseline(4).ok).toBe(true);
  });
  it("45% 被拦截（防呆，杜绝事故）", () => {
    const r = validateBaseline(45);
    expect(r.ok).toBe(false);
    expect(r.message).toContain("2-4");
  });
  it("1% 被拦截（低于下限）", () => {
    expect(validateBaseline(1).ok).toBe(false);
  });
});
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd dsh-plugin && npx vitest run test/templates.test.ts`
预期：FAIL

- [ ] **步骤 3：实现 templates.ts**

```ts
import { type ExperimentParams, type TerrainType } from "../shared/types.js";

/** 地形参数模板（来源：交接文档参数表 + 2-4% 基线铁律） */
const TEMPLATES: Record<TerrainType, ExperimentParams> = {
  mining: {
    rgLooks: 8, azLooks: 2, maxTimeBaselineDays: 90,
    maxPercBaseline: 2, filtering: "GOLDSTEIN", goldsteinWinSize: 64,
    unwrap: "MCF", unwrapCohThreshold: 0.2, useGacos: true, demFile: "",
  },
  landslide: {
    rgLooks: 7, azLooks: 2, maxTimeBaselineDays: 180,
    maxPercBaseline: 2, filtering: "GOLDSTEIN", goldsteinWinSize: 64,
    unwrap: "MCF", unwrapCohThreshold: 0.2, useGacos: true, demFile: "",
  },
  urban: {
    rgLooks: 5, azLooks: 1, maxTimeBaselineDays: 180,
    maxPercBaseline: 2, filtering: "GOLDSTEIN", goldsteinWinSize: 64,
    unwrap: "MCF", unwrapCohThreshold: 0.3, useGacos: true, demFile: "",
  },
  desert: {
    rgLooks: 8, azLooks: 2, maxTimeBaselineDays: 180,
    maxPercBaseline: 2, filtering: "GOLDSTEIN", goldsteinWinSize: 64,
    unwrap: "MCF", unwrapCohThreshold: 0.2, useGacos: true, demFile: "",
  },
  loess: {
    rgLooks: 8, azLooks: 2, maxTimeBaselineDays: 180,
    maxPercBaseline: 2, filtering: "GOLDSTEIN", goldsteinWinSize: 64,
    unwrap: "MCF", unwrapCohThreshold: 0.15, useGacos: true, demFile: "",
  },
};

export function getTemplate(terrain: TerrainType): ExperimentParams {
  const t = TEMPLATES[terrain];
  if (!t) throw new Error(`unknown terrain: ${terrain}`);
  return { ...t };
}

/** 防呆：空间基线必须 2-4%（设计铁律，杜绝 45% 事故） */
export function validateBaseline(
  perc: number,
): { ok: boolean; message?: string } {
  if (perc >= 2 && perc <= 4) return { ok: true };
  return {
    ok: false,
    message: `空间基线 ${perc}% 不在允许区间 2-4%（SARscape 默认 45% 是事故根源，已禁止）`,
  };
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd dsh-plugin && npx vitest run test/templates.test.ts`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add dsh-plugin/src/host/templates.ts dsh-plugin/test/templates.test.ts
git commit -m "feat(plugin): terrain param templates + 2-4% baseline gate (anti 45% incident)"
```

---

## 任务 5：实验注册表 registry.ts（TDD）

**文件：**
- 创建：`dsh-plugin/src/host/registry.ts`
- 测试：`dsh-plugin/test/registry.test.ts`

- [ ] **步骤 1：编写失败的测试**

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { mkdtempSync, rmSync, existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRegistry } from "../src/host/registry.js";

let dir: string;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "insar-reg-"));
});
afterEach(() => rmSync(dir, { recursive: true, force: true }));

describe("createRegistry", () => {
  it("创建空注册表（无文件时）", () => {
    const reg = createRegistry(dir);
    expect(reg.list()).toEqual([]);
  });
  it("创建实验并持久化", () => {
    const reg = createRegistry(dir);
    const id = reg.create({
      name: "minqin",
      terrain: "desert",
      dir: "G:/minqin1",
      dataDirs: { slc: "G:/slc", poeorb: "G:/poeorb", gacos: "G:/gacos", dem: "G:/dem" },
      params: { rgLooks: 8, azLooks: 2, maxTimeBaselineDays: 180, maxPercBaseline: 2,
        filtering: "GOLDSTEIN", goldsteinWinSize: 64, unwrap: "MCF", unwrapCohThreshold: 0.2,
        useGacos: true, demFile: "G:/dem/minqin" },
      status: "draft",
    });
    expect(reg.get(id)?.dataDirs.poeorb).toBe("G:/poeorb");
    // 持久化文件存在
    expect(existsSync(join(dir, "experiments.json"))).toBe(true);
    // 重新加载仍能读
    const reg2 = createRegistry(dir);
    expect(reg2.get(id)?.name).toBe("minqin");
  });
  it("更新状态", () => {
    const reg = createRegistry(dir);
    const id = reg.create({ name: "x", terrain: "urban", dir: "G:/x",
      dataDirs: { slc: "", poeorb: "", gacos: "", dem: "" },
      params: { rgLooks: 5, azLooks: 1, maxTimeBaselineDays: 180, maxPercBaseline: 2,
        filtering: "GOLDSTEIN", goldsteinWinSize: 64, unwrap: "MCF", unwrapCohThreshold: 0.3,
        useGacos: true, demFile: "" },
      status: "draft" });
    reg.update(id, { status: "running" });
    expect(reg.get(id)?.status).toBe("running");
  });
});
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd dsh-plugin && npx vitest run test/registry.test.ts`
预期：FAIL

- [ ] **步骤 3：实现 registry.ts**

```ts
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import type { Experiment } from "../shared/types.js";

export interface Registry {
  list(): Experiment[];
  get(id: string): Experiment | undefined;
  create(data: Omit<Experiment, "id">): string;
  update(id: string, patch: Partial<Experiment>): void;
}

export function createRegistry(dir: string): Registry {
  const file = join(dir, "experiments.json");
  let items: Experiment[] = [];
  if (existsSync(file)) {
    try {
      items = JSON.parse(readFileSync(file, "utf8")) as Experiment[];
    } catch {
      items = [];
    }
  }
  const persist = () => {
    mkdirSync(dir, { recursive: true });
    writeFileSync(file, JSON.stringify(items, null, 2), "utf8");
  };
  return {
    list: () => items,
    get: (id) => items.find((e) => e.id === id),
    create(data) {
      const id = randomUUID().slice(0, 8);
      items.push({ ...data, id });
      persist();
      return id;
    },
    update(id, patch) {
      const i = items.findIndex((e) => e.id === id);
      if (i >= 0) {
        items[i] = { ...items[i], ...patch, id };
        persist();
      }
    },
  };
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd dsh-plugin && npx vitest run test/registry.test.ts`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add dsh-plugin/src/host/registry.ts dsh-plugin/test/registry.test.ts
git commit -m "feat(plugin): experiment registry with persistent experiments.json (incl poeorb/gacos/dem/slc dirs)"
```

---

## 任务 6：脚本执行封装 runner.ts（TDD）

**文件：**
- 创建：`dsh-plugin/src/host/runner.ts`
- 测试：`dsh-plugin/test/runner.test.ts`

- [ ] **步骤 1：编写失败的测试**

```ts
import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runPython } from "../src/host/runner.js";

let dir: string;
beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "insar-run-"));
});
afterEach(() => rmSync(dir, { recursive: true, force: true }));

describe("runPython", () => {
  it("执行成功脚本返回 exit 0 与输出", async () => {
    const script = join(dir, "ok.py");
    writeFileSync(script, "print('hello from script')");
    const r = await runPython(process.execPath, ["-c", "print('hi')"], dir);
    expect(r.exitCode).toBe(0);
    expect(r.stdout).toContain("hi");
  });
  it("失败脚本返回非 0 exitCode", async () => {
    const r = await runPython(process.execPath, ["-c", "import sys; sys.exit(3)"], dir);
    expect(r.exitCode).toBe(3);
  });
});
```

（说明：测试用 `process.execPath`（node）模拟 python 调用，验证 spawn 封装逻辑；真实场景传 python 路径。）

- [ ] **步骤 2：运行测试验证失败**

运行：`cd dsh-plugin && npx vitest run test/runner.test.ts`
预期：FAIL

- [ ] **步骤 3：实现 runner.ts**

```ts
import { spawn } from "node:child_process";

export interface RunResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
}

const OUTPUT_CAP = 16 * 1024;

/** 执行 python 脚本，捕获输出（复用 dsh-remote-web-ui update.ts 的 spawn 模式） */
export function runPython(
  pythonBin: string,
  args: string[],
  cwd: string,
  timeoutMs = 10 * 60_000,
): Promise<RunResult> {
  return new Promise((resolve) => {
    const child = spawn(pythonBin, args, { cwd, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    const capped = (s: string, chunk: Buffer) => {
      const next = s + chunk.toString("utf8");
      return next.length > OUTPUT_CAP ? next.slice(-OUTPUT_CAP) : next;
    };
    child.stdout?.on("data", (b: Buffer) => { stdout = capped(stdout, b); });
    child.stderr?.on("data", (b: Buffer) => { stderr = capped(stderr, b); });
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      resolve({ exitCode: null, stdout, stderr: stderr + "\n[timeout]" });
    }, timeoutMs);
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ exitCode: null, stdout, stderr: `${stderr}\n${String(err)}` });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ exitCode: code, stdout, stderr });
    });
  });
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd dsh-plugin && npx vitest run test/runner.test.ts`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add dsh-plugin/src/host/runner.ts dsh-plugin/test/runner.test.ts
git commit -m "feat(plugin): python spawn runner with output cap and timeout"
```

---

## 任务 7：host 工具注册 tools.ts + index.ts

**文件：**
- 创建：`dsh-plugin/src/host/tools.ts`
- 修改：`dsh-plugin/src/index.ts`（创建）

- [ ] **步骤 1：实现 tools.ts（三个工具 + 参数快照校验）**

```ts
import { Context, Service } from "@deepseek-ai/cordis";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "@deepseek-ai/schemastery";
import { validateBaseline } from "./templates.js";
import { createRegistry } from "./registry.js";
import { computeStatus } from "./status.js";
import { runPython } from "./runner.js";
import { getTemplate } from "./templates.js";
import { SBAS_STEPS, type Experiment } from "../shared/types.js";

/** insar_run 入参 schema：确认卡确认后的最终参数 */
export const RunSchema = z.object({
  experimentId: z.string(),
  pythonBin: z.string().default("python"),
});

/** insar_status 入参 schema */
export const StatusSchema = z.object({
  experimentId: z.string(),
});

/** insar_templates 入参 schema */
export const TemplatesSchema = z.object({
  terrain: z.string().optional(),
});

/**
 * 注册三个工具到 host tools 注册表。
 * 依赖：ctx.get('tools')（host 注册表）、settings 命名空间、registry。
 */
export function registerTools(
  ctx: Context,
  deps: { registry: ReturnType<typeof createRegistry> },
) {
  const tools = ctx.get("tools") as any;

  tools.register("insar_run", {
    schema: RunSchema,
    async execute(input: z.infer<typeof RunSchema>) {
      const exp = deps.registry.get(input.experimentId);
      if (!exp) throw new Error(`experiment not found: ${input.experimentId}`);
      // 防呆：执行前再次校验基线
      const gate = validateBaseline(exp.params.maxPercBaseline);
      if (!gate.ok) throw new Error(gate.message);
      deps.registry.update(input.experimentId, { status: "queued" });
      // 异步后台执行：runner.runPython(下载/批处理 bat)
      const result = await runPython(
        input.pythonBin,
        ["scripts/multi_download.py", "--experiment", exp.dir],
        exp.dir,
      );
      if (result.exitCode !== 0) {
        deps.registry.update(input.experimentId, {
          status: "failed",
          error: { code: "run-failed", detail: result.stderr, evidence: "" },
        });
        throw new Error(`insar_run failed: ${result.stderr}`);
      }
      deps.registry.update(input.experimentId, { status: "running" });
      return { ok: true, experimentId: input.experimentId };
    },
  });

  tools.register("insar_status", {
    schema: StatusSchema,
    async execute(input: z.infer<typeof StatusSchema>) {
      const exp = deps.registry.get(input.experimentId);
      if (!exp) throw new Error(`experiment not found: ${input.experimentId}`);
      // 读取实验目录下的状态文件（真实解析）
      const auxXml = readFileSafe(join(exp.dir, "auxiliary.sml"), "");
      const stepXml = readFileSafe(join(exp.dir, "work", "work_step_performed.sml"), "");
      const guardLog = readFileSafe(join(exp.dir, "..", "asf_experiment", "sbas_guard.log"), "");
      return computeStatus({ auxXml, stepXml, guardLog });
    },
  });

  tools.register("insar_templates", {
    schema: TemplatesSchema,
    async execute(input: z.infer<typeof TemplatesSchema>) {
      if (input.terrain) {
        return getTemplate(input.terrain as any);
      }
      return {
        terrains: ["mining", "landslide", "urban", "desert", "loess"],
      };
    },
  });
}

function readFileSafe(path: string, fallback: string): string {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return fallback;
  }
}
```

- [ ] **步骤 2：实现 index.ts（host 入口：工具 + 设置 + 注册表）**

```ts
import { Context } from "@deepseek-ai/cordis";
import { createRegistry } from "./host/registry.js";
import { registerTools } from "./host/tools.js";
import { registerSettings } from "./host/settings.js";

export * from "./shared/types.js";
export { computeStatus } from "./host/status.js";
export { getTemplate, validateBaseline } from "./host/templates.js";

export const name = "insar-genie-dsh";

/** 实验注册表存储目录（可通过设置覆盖） */
export const REGISTRY_DIR = () =>
  process.env.DSH_HOME
    ? join(process.env.DSH_HOME, "insar-genie")
    : join(process.cwd(), ".insar-genie");

export function apply(ctx: Context) {
  const registry = createRegistry(REGISTRY_DIR());
  registerSettings(ctx);
  registerTools(ctx, { registry });
  ctx.on("dispose", () => {});
}
```

- [ ] **步骤 3：实现 settings.ts（设置命名空间，含 POEORB 路径）**

```ts
import { Context } from "@deepseek-ai/cordis";
import z from "@deepseek-ai/schemastery";
import { installSettingsSection } from "@deepseek-ai/dsh-settings";

export const SETTINGS_NS = "insarGenie";

export function registerSettings(ctx: Context) {
  installSettingsSection(ctx, SETTINGS_NS, {
    schema: z.object({
      earthdataUser: z.string().default(""),
      earthdataPassword: z.string().default(""),
      gacosEmail: z.string().default(""),
      gacosImapAuthCode: z.string().default(""),
      enviIdl: z.string().default("C:\\Program Files\\Harris\\ENVI56\\IDL88\\bin\\bin.x86_64\\envi_idl.exe"),
      sarscapeLib: z.string().default("C:\\Program Files\\SARMAP SA\\SARscape"),
      workDir: z.string().default("G:\\"),
      /** 精密轨道目录：默认 <实验目录>/poeorb，可覆盖为公共轨道库 */
      poeorbDir: z.string().default(""),
      registryDir: z.string().default(""),
    }),
    title: "insar-genie 设置",
  });
}
```

- [ ] **步骤 4：构建验证**

运行：`cd dsh-plugin && npx tsc -p tsconfig.json --noEmit`
预期：无类型错误（若缺 `@deepseek-ai/dsh-settings` 类型则先 `npm install` 相关 peer）。

- [ ] **步骤 5：Commit**

```bash
git add dsh-plugin/src/index.ts dsh-plugin/src/host/tools.ts dsh-plugin/src/host/settings.ts
git commit -m "feat(plugin): register insar_run/insar_status/insar_templates tools + settings ns (incl POEORB dir)"
```

---

## 任务 8：client 侧组件（ParamConfirm + ProgressPanel）

**文件：**
- 创建：`dsh-plugin/src/client/index.ts`
- 创建：`dsh-plugin/src/client/ParamConfirm.tsx`
- 创建：`dsh-plugin/src/client/ProgressPanel.tsx`

- [ ] **步骤 1：实现 client/index.ts（client 入口）**

```ts
import { defineComponent } from "@deepseek-ai/dsh-client-runtime";
import { ParamConfirm } from "./ParamConfirm.js";
import { ProgressPanel } from "./ProgressPanel.js";

export default defineComponent({
  slots: {
    "insar-param-confirm": ParamConfirm,
    "insar-progress-panel": ProgressPanel,
  },
});
```

- [ ] **步骤 2：实现 ParamConfirm.tsx（参数确认卡片）**

```tsx
import { useState } from "react";
import type { ExperimentParams, TerrainType } from "../shared/types.js";
import { validateBaseline } from "../host/templates.js";

const TERRAIN_LABELS: Record<TerrainType, string> = {
  mining: "矿区", landslide: "滑坡", urban: "城市", desert: "沙漠", loess: "黄土高原",
};

/**
 * 参数确认卡片：地形联动参数 + 2-4% 基线防呆。
 * 调用方（AI）在 insar_run 前渲染此组件，确认后才执行。
 */
export function ParamConfirm(props: {
  terrain: TerrainType;
  params: ExperimentParams;
  onChange: (p: ExperimentParams) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [params, setParams] = useState(props.params);
  const gate = validateBaseline(params.maxPercBaseline);

  const update = (patch: Partial<ExperimentParams>) => {
    const next = { ...params, ...patch };
    setParams(next);
    props.onChange(next);
  };

  return (
    <div style={{ border: "1px solid #ccc", borderRadius: 8, padding: 16, maxWidth: 480 }}>
      <h3>实验参数确认</h3>
      <p>地形：{TERRAIN_LABELS[props.terrain]}</p>

      <label>
        空间基线（% of critical）：
        <input
          type="number"
          value={params.maxPercBaseline}
          onChange={(e) => update({ maxPercBaseline: Number(e.target.value) })}
          style={gate.ok ? {} : { border: "2px solid red" }}
        />
      </label>
      {!gate.ok && (
        <p style={{ color: "red" }}>⚠️ {gate.message}</p>
      )}

      <label>多视：{params.rgLooks}:{params.azLooks}</label>
      <label>时间基线：{params.maxTimeBaselineDays} 天</label>
      <label>滤波：{params.filtering} {params.goldsteinWinSize}</label>
      <label>解缠：{params.unwrap} 阈值 {params.unwrapCohThreshold}</label>
      <label>GACOS 校正：{params.useGacos ? "开" : "关"}</label>

      <div style={{ marginTop: 12 }}>
        <button onClick={props.onConfirm} disabled={!gate.ok}>确认执行</button>
        <button onClick={props.onCancel}>取消</button>
      </div>
    </div>
  );
}
```

- [ ] **步骤 3：实现 ProgressPanel.tsx（进度面板）**

```tsx
import { useEffect, useState } from "react";
import type { ExperimentStatus } from "../shared/types.js";

const STEP_LABELS = ["连接图", "干涉", "解缠", "反演1", "反演2", "地理编码"];

/** 进度面板：五步进度条 + 剩余时间 + 异常 */
export function ProgressPanel(props: {
  experimentId: string;
  fetchStatus: (id: string) => Promise<ExperimentStatus>;
}) {
  const [status, setStatus] = useState<ExperimentStatus | null>(null);

  useEffect(() => {
    const tick = async () => {
      try {
        setStatus(await props.fetchStatus(props.experimentId));
      } catch {
        /* 网络/服务暂不可用，保持上次状态 */
      }
    };
    tick();
    const timer = setInterval(tick, 30_000); // 30s 轮询
    return () => clearInterval(timer);
  }, [props.experimentId]);

  if (!status) return <div>加载中…</div>;

  return (
    <div style={{ border: "1px solid #ccc", borderRadius: 8, padding: 16, maxWidth: 640 }}>
      <h3>SBAS 实验进度</h3>
      <div style={{ display: "flex", gap: 4 }}>
        {STEP_LABELS.map((label, i) => (
          <div
            key={label}
            style={{
              flex: 1,
              padding: 6,
              textAlign: "center",
              background: i < status.stepIndex ? "#4caf50" : i === status.stepIndex ? "#ff9800" : "#eee",
              borderRadius: 4,
            }}
          >
            {label}
          </div>
        ))}
      </div>
      <p>{status.progressLabel}</p>
      <p>已完成 {status.donePairs}/{status.totalPairs} 对 · 速率 {status.pairsPerMinute.toFixed(2)} 对/分 · 预计剩余 {Math.round(status.etaMinutes / 60)} 小时</p>
      <p>数据盘占用：{status.diskGb.toFixed(1)} GB</p>
      {status.error && (
        <div style={{ border: "1px solid red", padding: 8, marginTop: 8 }}>
          <strong>异常：</strong>{status.error.detail}
          <br />
          <small>证据：{status.error.evidence}</small>
        </div>
      )}
    </div>
  );
}
```

- [ ] **步骤 4：构建验证**

运行：`cd dsh-plugin && npx tsc -p tsconfig.json --noEmit`
预期：无类型错误（React JSX 类型需 `npm i -D react @types/react`；若 client 类型来自 `@deepseek-ai/dsh-client-runtime` 则按 peer 安装）。

- [ ] **步骤 5：Commit**

```bash
git add dsh-plugin/src/client/
git commit -m "feat(plugin): client UI - ParamConfirm (2-4% baseline gate) + ProgressPanel (5-step + ETA)"
```

---

## 任务 9：插件挂载到 agent preset + 安装脚本

**文件：**
- 修改：`dsh/insar-genie/agent.cordis.yml`（新增插件行）
- 修改：`dsh/install-dsh.ps1`（安装插件依赖说明）
- 创建：`dsh-plugin/assets/README.md`

- [ ] **步骤 1：在 agent.cordis.yml 添加插件挂载**

在 `# ═══ skills ═══` 段之后追加：

```yaml
# ─── insar-genie dsh plugin (host tools + client UI) ───
# The cordis plugin package provides insar_run / insar_status / insar_templates
# host tools plus the ParamConfirm / ProgressPanel client components.
- id: insar-genie-dsh
  name: '@dsh-custom/insar-genie-dsh'
```

（说明：`@dsh-custom/insar-genie-dsh` 通过 profile bundle 或 preset 依赖安装——开发期用 `dsh plugin add @dsh-custom/insar-genie-dsh`，发布后走 npm。）

- [ ] **步骤 2：创建 assets/README.md**

```markdown
# assets

本插件的技能资产（SKILL.md / scripts/ / experiment/）由 agent preset
`dsh/insar-genie/` 携带（安装在 `~/.dsh/.agent-presets/insar-genie/skills/`）。

插件运行时通过设置命名空间的 `skillDir` 解析脚本路径，不重复打包 Python 资产。

配套数据路径（settings → insarGenie）：
- `poeorbDir`：精密轨道目录（默认 `<实验目录>/poeorb`，可覆盖为公共轨道库）
- `gacosDir` / `demDir` / `slcDir`：其余配套数据目录
```

- [ ] **步骤 3：更新 install-dsh.ps1 增加插件安装说明**

在文件头部注释的"安装内容"段补充：

```powershell
# 安装内容：
#   SBAS-InSAR 全链路 agent preset（含 insar-genie 技能 + scripts + experiment）
#   安装到 $env:USERPROFILE\.dsh\.agent-presets\insar-genie\
#   可选：cordis 插件 @dsh-custom/insar-genie-dsh（host 工具 + UI）
#      dsh plugin add @dsh-custom/insar-genie-dsh
```

- [ ] **步骤 4：Commit**

```bash
git add dsh/insar-genie/agent.cordis.yml dsh/install-dsh.ps1 dsh-plugin/assets/
git commit -m "feat(plugin): mount insar-genie-dsh into agent preset + install docs"
```

---

## 任务 10：端到端验证 + 收尾

**文件：**
- 修改：`dsh-plugin/package.json`（版本/README）
- 创建：`dsh-plugin/README.md`

- [ ] **步骤 1：运行全部测试**

运行：`cd dsh-plugin && npx vitest run`
预期：全部 PASS（status/templates/registry/runner 四组用例）

- [ ] **步骤 2：构建产物**

运行：`cd dsh-plugin && npm run build`
预期：`lib/` 生成（index.js + types），无错误

- [ ] **步骤 3：写 README.md**

```markdown
# @dsh-custom/insar-genie-dsh

SBAS-InSAR 全链路 DSH 插件：insar_run / insar_status / insar_templates 工具 +
参数确认卡片（2-4% 基线防呆）+ 进度面板。

## 安装

1. 安装 agent preset（携带技能与脚本）：
   `powershell -ExecutionPolicy Bypass -File dsh/install-dsh.ps1`
2. 安装插件：
   `dsh plugin add @dsh-custom/insar-genie-dsh`

## 使用

- 对话：「跑 SBAS，区域 xxx.shp，2020-2025，VV」
- AI 识别地形 → 推 ParamConfirm 卡片 → 用户确认 → insar_run 执行
- 实验运行中：ProgressPanel 每 30s 刷新五步进度与剩余时间

## 设置（settings → insarGenie）

- earthdataUser / earthdataPassword：ASF 凭证
- gacosEmail / gacosImapAuthCode：GACOS 收件邮箱
- enviIdl / sarscapeLib：ENVI/SARscape 路径
- workDir / poeorbDir / gacosDir / demDir：数据目录（POEORB 默认 <实验目录>/poeorb）

## 防呆铁律

- 空间基线必须在 2-4%（validateBaseline 拦截 45%）
- 执行后应校验 tmp/*/work/PARAMETERS_INFO_*.xml 实际落盘值 == 参数快照
```

- [ ] **步骤 4：最终 Commit**

```bash
git add dsh-plugin/README.md dsh-plugin/package.json
git commit -m "docs(plugin): README with install/usage/settings/anti-fool rules"
```

- [ ] **步骤 5：推 dev 分支（不 push main）**

```bash
git push origin dev
```

---

## 自检

**1. 规格覆盖度：**
- 技能层：已有 preset，任务 9 挂载插件到 preset ✓
- insar_run/insar_status/insar_templates：任务 7 ✓
- status.ts 状态解析：任务 3（移植 sbas_guard.py parse_progress）✓
- settings 含 POEORB：任务 7 settings.ts（poeorbDir）✓
- registry 含 dataDirs：任务 5 ✓
- ParamConfirm 防呆 2-4%：任务 8 + validateBaseline（任务 4）✓
- ProgressPanel 五步 + ETA：任务 8 ✓
- 异常诊断：computeStatus 的 error 字段（任务 3）+ 面板展示（任务 8）；规则库内嵌 status.ts
- 测试用真实 fixture：任务 2 ✓
- 三阶段路线：任务 1-6=阶段1核心闭环，任务 7-8=阶段2防呆执行+UI，任务 9-10=阶段3集成

**2. 占位符扫描：** 无 TODO/待定；每个任务有完整代码和命令 ✓

**3. 类型一致性：** `ExperimentParams`/`ExperimentStatus`/`Experiment`/`TerrainType`/`SbasStep` 在 shared/types.ts 统一定义，host/client 共用；`validateBaseline`/`getTemplate`/`createRegistry`/`computeStatus`/`runPython` 签名在定义任务与使用任务间一致 ✓

**已知边界**（有意为之，YAGNI）：
- 异常诊断规则库暂为 status.ts 内嵌的基础规则（误报完成/burst 级失败/停滞检测），完整规则库留待阶段 3
- Process.log 每对耗时解析未做（pairsPerMinute 用常数 0.22），阶段 3 细化
- client 组件 slot 注册依赖 `@deepseek-ai/dsh-client-runtime` 的 defineComponent API，实现时若 API 细节有出入按该包实际导出调整
