import type { ReactNode } from "react";

/** 五步进度标签（与 host status.ts 一致） */
export const STEP_LABELS = ["连接图", "干涉", "解缠", "反演1", "反演2", "地理编码"] as const;

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
  error?: { code: string; detail: string; evidence: string };
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

export const TERRAIN_LABELS: Record<TerrainType, string> = {
  mining: "矿区",
  landslide: "滑坡",
  urban: "城市",
  desert: "沙漠",
  loess: "黄土高原",
};

/**
 * 防呆：空间基线必须在 2-4%（杜绝 45% 事故）。
 * 与 host templates.ts 的 validateBaseline 语义一致。
 */
export function validateBaseline(perc: number): { ok: boolean; message?: string } {
  if (perc >= 2 && perc <= 4) return { ok: true };
  return {
    ok: false,
    message: `空间基线 ${perc}% 不在允许区间 2-4%（SARscape 默认 45% 是事故根源，已禁止）`,
  };
}

/** turnTail 插槽渲染的通用包装（简单卡片容器） */
export function PanelCard(props: { title: string; children: ReactNode }): ReactNode {
  return (
    <div style={{ border: "1px solid #ccc", borderRadius: 8, padding: 12, margin: "8px 0", maxWidth: 640 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{props.title}</div>
      {props.children}
    </div>
  );
}
