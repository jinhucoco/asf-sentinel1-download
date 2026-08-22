import { readFileSync } from "node:fs";
import { join } from "node:path";
import { defineTool } from "@deepseek-ai/dsh-tools";
import { validateBaseline, getTemplate } from "./templates.js";
import { createRegistry } from "./registry.js";
import { computeStatus } from "./status.js";
import { runPython } from "./runner.js";

/** 通用输出：宽松 object schema + JSON 文本渲染（同 dsh-tool-goal 的 GOAL_OUTPUT） */
const JSON_OUTPUT = {
  schema: { type: "object", additionalProperties: true },
  render: (_args: unknown, value: unknown): { type: "text"; text: string }[] => [{
    type: "text",
    text: JSON.stringify(value) ?? "",
  }],
} as const;

/**
 * 注册三个工具到 host tools 注册表。
 * 依赖：ctx.tools（host 工具运行时）、registry。
 */
export function registerTools(
  ctx: any,
  deps: { registry: ReturnType<typeof createRegistry> },
) {
  ctx.tools.register(defineTool({
    name: "insar_run",
    description: "Execute an insar-genie experiment step (download/batch) after param-confirm gate. Async: creates a background run and returns immediately.",
    parameters: {
      experimentId: { type: "string", required: true, description: "Experiment id from the registry." },
      pythonBin: { type: "string", description: "Python executable path. Defaults to 'python'." },
    },
    output: JSON_OUTPUT,
    async execute(input: { experimentId: string; pythonBin?: string }) {
      const exp = deps.registry.get(input.experimentId);
      if (!exp) throw new Error(`experiment not found: ${input.experimentId}`);
      // 防呆：执行前再次校验基线（2-4%，杜绝 45% 事故）
      const gate = validateBaseline(exp.params.maxPercBaseline);
      if (!gate.ok) throw new Error(gate.message);
      deps.registry.update(input.experimentId, { status: "queued" });
      const result = await runPython(
        input.pythonBin ?? "python",
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
  }));

  ctx.tools.register(defineTool({
    name: "insar_status",
    description: "Read an experiment's current SBAS progress (connection graph → geocoding) from its status files.",
    parameters: {
      experimentId: { type: "string", required: true, description: "Experiment id from the registry." },
    },
    output: JSON_OUTPUT,
    execute(input: { experimentId: string }) {
      const exp = deps.registry.get(input.experimentId);
      if (!exp) throw new Error(`experiment not found: ${input.experimentId}`);
      const auxXml = readFileSafe(join(exp.dir, "auxiliary.sml"), "");
      const stepXml = readFileSafe(join(exp.dir, "work", "work_step_performed.sml"), "");
      const guardLog = readFileSafe(join(exp.dir, "..", "asf_experiment", "sbas_guard.log"), "");
      // 注：status.ts 的参数名是 stepPerformedXml（简报原文 stepXml 与现有代码不一致，已适配）
      return Promise.resolve(computeStatus({ auxXml, stepPerformedXml: stepXml, guardLog }) as never);
    },
  }));

  ctx.tools.register(defineTool({
    name: "insar_templates",
    description: "Return a terrain parameter template (mining/landslide/urban/desert/loess) or the terrain list.",
    parameters: {
      terrain: { type: "string", description: "Terrain type; omit to list all." },
    },
    output: JSON_OUTPUT,
    execute(input: { terrain?: string }) {
      if (input.terrain) {
        // 注：getTemplate 返回 interface ExperimentParams，无隐式索引签名，故 as never 适配 Record<string, JsonValue>
        return Promise.resolve(getTemplate(input.terrain as never) as never);
      }
      return Promise.resolve({
        terrains: ["mining", "landslide", "urban", "desert", "loess"],
      });
    },
  }));
}

function readFileSafe(path: string, fallback: string): string {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return fallback;
  }
}
