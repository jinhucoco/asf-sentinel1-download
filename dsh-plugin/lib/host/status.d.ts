import { type ExperimentStatus } from "../shared/types.js";
/** 解析 auxiliary.sml 各步骤 OK/NotOK → {tag: bool}（移植自 sbas_guard.py parse_progress） */
export declare function parseAuxiliarySteps(xml: string): Record<string, boolean>;
/** 从 work_step_performed.sml 计算已完成对/总对（第三列=1 为完成） */
export declare function parsePairProgress(xml: string): {
    done: number;
    total: number;
};
/** 从 guard.log 提取最后一条体检进度 + 动态速率。
 *  速率 = 最后两条体检记录的 (对数差 ÷ 分钟差)，夹在 [0.01, 5] 对/分钟，
 *  无可算（不足两条/时间倒退）时返回 0 由调用方兜底。 */
export declare function parseGuardLog(log: string): {
    donePairs: number;
    totalPairs: number;
    diskGb: number;
    pairsPerMinute: number;
};
/** 组合完整状态 */
export declare function computeStatus(input: {
    auxXml: string;
    stepPerformedXml: string;
    guardLog: string;
}): ExperimentStatus;
