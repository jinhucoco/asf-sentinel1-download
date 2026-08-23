import { type ExperimentParams, type TerrainType } from "../shared/types.js";

export { validateBaseline } from "../shared/baseline.js";

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
