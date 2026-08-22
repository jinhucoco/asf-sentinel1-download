import { readFileSync } from "node:fs";
import { join } from "node:path";
import { defineTool } from "@deepseek-ai/dsh-tools";
import { getTemplate } from "./templates.js";
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
    description: "Run the ASF Sentinel-1 SLC downloader (skill scripts/multi_download.py) with the given download inputs. Synchronous await: the download runs to completion — hours for large AOIs — so do not expect an immediate return. Provide either a manifest CSV (list) or an AOI + time range (aoi/start/end); pass pol/out to control polarization and destination.",
    parameters: {
      scriptDir: { type: "string", required: true, description: "Directory containing the skill scripts (multi_download.py lives here), e.g. <repo>/skills/insar-genie/scripts. Used as the process cwd." },
      list: { type: "string", description: "Manifest CSV path (columns: date,frame,orbit,satellite,file). List-driven path; takes precedence over aoi/start/end." },
      aoi: { type: "string", description: "AOI shapefile/kml path. Search-driven path; requires start and end." },
      start: { type: "string", description: "Start date YYYYMMDD (search-driven path)." },
      end: { type: "string", description: "End date YYYYMMDD (search-driven path)." },
      pol: { type: "string", description: "Polarization(s), comma-separated, e.g. 'VV+VH,VV'. Defaults to 'VV+VH,VV'." },
      out: { type: "string", description: "Download output directory. Defaults to '<scriptDir>/sentinel1_data'." },
      pythonBin: { type: "string", description: "Python executable path. Defaults to 'python'." },
    },
    output: JSON_OUTPUT,
    async execute(input: {
      scriptDir: string;
      list?: string;
      aoi?: string;
      start?: string;
      end?: string;
      pol?: string;
      out?: string;
      pythonBin?: string;
    }) {
      const args = ["multi_download.py"];
      if (input.list) {
        // 清单驱动（与 multi_download.py 的 "list 优先于搜索路径" 语义一致）
        args.push("--list", input.list);
      } else {
        if (!input.aoi || !input.start || !input.end) {
          throw new Error("insar_run: provide either list (manifest CSV) or aoi + start + end (search-driven download)");
        }
        args.push("--aoi", input.aoi, "--start", input.start, "--end", input.end);
      }
      if (input.pol) args.push("--pol", input.pol);
      if (input.out) args.push("--out", input.out);
      // 同步 await：数小时级下载，不设超时（runPython timeoutMs 缺省为 undefined）
      const result = await runPython(
        input.pythonBin ?? "python",
        args,
        input.scriptDir,
      );
      if (result.exitCode !== 0) {
        throw new Error(`insar_run failed: ${result.stderr}`);
      }
      return { ok: true, args, stdout: result.stdout };
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
