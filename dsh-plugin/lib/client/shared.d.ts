import type { ReactNode } from "react";
import { validateBaseline } from "../shared/baseline.js";
export { validateBaseline };
/** 五步进度标签（与 host status.ts 一致） */
export declare const STEP_LABELS: readonly ["连接图", "干涉", "解缠", "反演1", "反演2", "地理编码"];
/** 进度快照（与 host shared/types.ts 的 ExperimentStatus 对齐；client 独立声明避免 host 依赖） */
export interface ProgressSnapshot {
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
/** 参数确认快照（与 host ExperimentParams 对齐） */
export interface ParamSnapshot {
    rgLooks: number;
    azLooks: number;
    maxTimeBaselineDays: number;
    maxPercBaseline: number;
    filtering: string;
    goldsteinWinSize: number;
    unwrap: string;
    unwrapCohThreshold: number;
    useGacos: boolean;
    demFile: string;
}
export type TerrainType = "mining" | "landslide" | "urban" | "desert" | "loess";
export declare const TERRAIN_LABELS: Record<TerrainType, string>;
/** turnTail 插槽渲染的通用包装（简单卡片容器） */
export declare function PanelCard(props: {
    title: string;
    children: ReactNode;
}): ReactNode;
