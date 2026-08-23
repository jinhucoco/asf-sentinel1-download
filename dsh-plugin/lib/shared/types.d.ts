/** 实验生命周期状态 */
export type ExperimentLifecycle = "draft" | "queued" | "running" | "paused" | "failed" | "done";
/** SBAS 五步（对应 auxiliary.sml 的 OK/NotOK 标记） */
export declare const SBAS_STEPS: readonly ["generate_connection_graph", "interf_stack", "unwrapping", "first_inversion", "second_inversion", "geocode_result"];
export type SbasStep = (typeof SBAS_STEPS)[number];
/** 一个实验的完整记录 */
export interface Experiment {
    id: string;
    name: string;
    terrain: TerrainType;
    dir: string;
    dataDirs: {
        slc: string;
        poeorb: string;
        gacos: string;
        dem: string;
    };
    params: ExperimentParams;
    status: ExperimentLifecycle;
    startedAt?: string;
    error?: {
        code: string;
        detail: string;
        evidence: string;
    };
}
/** 地形类型（模板库键） */
export type TerrainType = "mining" | "landslide" | "urban" | "desert" | "loess";
/** 参数快照（防呆：空间基线必须是 2-4%） */
export interface ExperimentParams {
    rgLooks: number;
    azLooks: number;
    maxTimeBaselineDays: number;
    maxPercBaseline: number;
    filtering: "GOLDSTEIN";
    goldsteinWinSize: number;
    unwrap: "MCF";
    unwrapCohThreshold: number;
    useGacos: boolean;
    demFile: string;
}
/** insar_status 返回的进度快照 */
export interface ExperimentStatus {
    step: SbasStep;
    stepIndex: number;
    totalSteps: number;
    donePairs: number;
    totalPairs: number;
    pairsPerMinute: number;
    etaMinutes: number;
    diskGb: number;
    progressLabel: string;
    isStalled: boolean;
    error?: {
        code: string;
        detail: string;
        evidence: string;
    };
}
