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
