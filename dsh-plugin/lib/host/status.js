import { SBAS_STEPS } from "../shared/types.js";
/** 解析 auxiliary.sml 各步骤 OK/NotOK → {tag: bool}（移植自 sbas_guard.py parse_progress） */
export function parseAuxiliarySteps(xml) {
    const out = {};
    const re = /<(\w+)>(OK|NotOK)<\/\1>/g;
    let m;
    while ((m = re.exec(xml)) !== null) {
        out[m[1]] = m[2] === "OK";
    }
    return out;
}
/** 从 work_step_performed.sml 计算已完成对/总对（第三列=1 为完成） */
export function parsePairProgress(xml) {
    const totalMatch = /NumberOfRows\s*=\s*"(\d+)"/.exec(xml);
    const total = totalMatch ? Number(totalMatch[1]) : 0;
    const done = (xml.match(/<ValueInteger ID = "2">1<\/ValueInteger>/g) ?? []).length;
    return { done, total };
}
/** 从 guard.log 提取最后一条体检进度 + 动态速率。
 *  速率 = 最后两条体检记录的 (对数差 ÷ 分钟差)，夹在 [0.01, 5] 对/分钟，
 *  无可算（不足两条/时间倒退）时返回 0 由调用方兜底。 */
export function parseGuardLog(log) {
    const lines = log.trim().split("\n").filter((l) => l.includes("体检"));
    const last = lines[lines.length - 1] ?? "";
    const pair = /(\d+)\/(\d+) 对/.exec(last);
    const disk = /([\d.]+)G/.exec(last);
    // 动态速率：用最后两条体检记录推算
    let pairsPerMinute = 0;
    if (lines.length >= 2) {
        const prev = lines[lines.length - 2];
        const pprev = /(\d+)\/(\d+) 对/.exec(prev);
        const timeRe = /\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]/;
        const tPrev = timeRe.exec(prev)?.[1];
        const tLast = timeRe.exec(last)?.[1];
        if (pprev && tPrev && tLast && pprev[1]) {
            const dMin = (Date.parse(tLast.replace(" ", "T")) - Date.parse(tPrev.replace(" ", "T"))) / 60000;
            const dPairs = Number(pair?.[1] ?? 0) - Number(pprev[1]);
            if (dMin > 0 && dPairs > 0) {
                const rate = dPairs / dMin;
                // 夹在合理区间，避免除以极小时间段导致爆值
                pairsPerMinute = Math.min(5, Math.max(0.01, rate));
            }
        }
    }
    return {
        donePairs: pair ? Number(pair[1]) : 0,
        totalPairs: pair ? Number(pair[2]) : 0,
        diskGb: disk ? Number(disk[1]) : 0,
        pairsPerMinute,
    };
}
/** 组合完整状态 */
export function computeStatus(input) {
    // 数据源缺失：返回结构化 error 而非误导的全零状态（AI/面板能区分"未开始"与"读不到文件"）
    if (!input.auxXml.trim()) {
        return {
            step: "generate_connection_graph",
            stepIndex: 0,
            totalSteps: SBAS_STEPS.length,
            donePairs: 0,
            totalPairs: 0,
            pairsPerMinute: 0,
            etaMinutes: 0,
            diskGb: 0,
            progressLabel: "无法读取进度文件",
            isStalled: false,
            error: {
                code: "no-auxiliary",
                detail: "auxiliary.sml 缺失或不可读，无法确定实验进度",
                evidence: "",
            },
        };
    }
    const aux = parseAuxiliarySteps(input.auxXml);
    const { done, total } = parsePairProgress(input.stepPerformedXml);
    const guard = parseGuardLog(input.guardLog);
    // 当前步骤 = 第一个 NotOK 的 SBAS 步骤
    let stepIndex = SBAS_STEPS.findIndex((s) => !aux[s]);
    if (stepIndex === -1)
        stepIndex = SBAS_STEPS.length - 1;
    const step = SBAS_STEPS[stepIndex];
    const stepLabels = {
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
    // 速率：优先用 guard 动态速率，无则兜底硬编码 0.22（4.5 分/对）
    const ppm = guard.pairsPerMinute > 0 ? guard.pairsPerMinute : 0.22;
    return {
        step,
        stepIndex,
        totalSteps: SBAS_STEPS.length,
        donePairs,
        totalPairs,
        pairsPerMinute: ppm,
        etaMinutes: totalPairs > 0 ? Math.round((totalPairs - donePairs) / ppm) : 0,
        diskGb: guard.diskGb,
        progressLabel: `${stepLabels[step]} ${pct}%`,
        isStalled: false,
    };
}
